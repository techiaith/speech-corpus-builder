import os
import sys
import time

import shlex
import subprocess
import hashlib

import cld3

import pandas as pd

from pathlib import Path
from tqdm import tqdm
from pydub import AudioSegment

from corpus_database import corpus_database
from corpus_statistics import get_summary

from speech_to_text.speech_to_text import SpeechToText


#
# see https://github.com/ytdl-org/youtube-dl/blob/master/README.md#output-template
YOUTUBE_DL_COMMAND_TEMPLATE="""yt-dlp --download-archive {downloads_dir}/downloaded.txt \
    --rm-cache-dir -cwi --no-post-overwrites \
    -o {downloads_dir}'/%(id)s__%(title)s.%(ext)s' --restrict-filenames \
    --cookies={downloads_dir}/cookies.txt \
    --extract-audio --audio-format mp3 https://www.youtube.com/@{channel_name}
"""
        
FFMPEG_COMMAND_TEMPLATE="ffmpeg -y -i {mp3_file_path} -hide_banner -nostats -loglevel error -vn -acodec pcm_s16le -ar 16000 -ac 1 {wav_file_path}"


#
class youtube_corpus:

    def __init__(self, corpus_root_dir):
        
        self.corpus_database = corpus_database(corpus_root_dir)
        
        self.downloads_root_dir=os.path.join(corpus_root_dir, "downloads")
        self.dataset_root_dir=os.path.join(corpus_root_dir, "dataset")
        self.dataset_clips_dir=os.path.join(self.dataset_root_dir, "clips")

        self.speech_to_text=SpeechToText()

        Path(self.downloads_root_dir).mkdir(parents=True, exist_ok=True)
        Path(self.dataset_root_dir).mkdir(parents=True, exist_ok=True)
        Path(self.dataset_clips_dir).mkdir(parents=True, exist_ok=True)
        


    def download_channel(self, channel_name):
        # channel could endswith 'streams'
        downloads_dir = os.path.join(self.downloads_root_dir, channel_name.replace("/","_"))
        Path(downloads_dir).mkdir(parents=True, exist_ok=True)
 
        cmd = YOUTUBE_DL_COMMAND_TEMPLATE.format(downloads_dir=downloads_dir, channel_name=channel_name)
        subprocess.run(shlex.split(cmd), stderr=sys.stderr, stdout=sys.stdout)

        return downloads_dir
    


    def dbimport_all_downloads(self):
        
        for mp3_file_path in self.iterate_downloads_folder():
            mp3_file = Path(mp3_file_path)
            mp3_file_name = mp3_file.name
            mp3_file_name_elements = mp3_file_name.split("__")
            #
            yt_id = mp3_file_name_elements[0]
            yt_name = mp3_file_name_elements[1]
            yt_name = yt_name.replace(".mp3","")
            yt_source = mp3_file.parent.name

            self.corpus_database.add_audio_source(source_type="youtube", source_id=yt_id, source_channel=yt_source, 
                                                  source_name=yt_name, source_url="https://youtu.be/"+yt_id, source_file_path=mp3_file_path)



    def create_transcribed_clips(self):

        def generate_md5_hex(audio_segment):
            return hashlib.md5(audio_segment.raw_data).hexdigest()

        audio_files = self.corpus_database.get_all_audio_files_requiring_transcribing(self.speech_to_text.wav2vec2_model_path)
        for audio_file in tqdm(audio_files):

            # convert mp3 to wav file..
            mp3_file=Path(audio_file["source_file_path"])
            
            destination_wav_file_path=os.path.join(mp3_file.parent, mp3_file.name.replace(".mp3", ".wav"))
            cmd = FFMPEG_COMMAND_TEMPLATE.format(mp3_file_path=mp3_file.as_posix(), wav_file_path=destination_wav_file_path)
            subprocess.run(shlex.split(cmd), stderr=sys.stderr, stdout=sys.stdout) 

            #
            wav_audio_file = AudioSegment.from_wav(destination_wav_file_path)
            tqdm.write("{}, duration {} seconds.".format(mp3_file.as_posix(), wav_audio_file.duration_seconds))
                                 
            #         
            transcriptions = list()
            start_time = time.time()
            for transcript, confidence, time_start, time_end, alignments in self.speech_to_text.transcribe(destination_wav_file_path, withlm=False):
               
                if len(transcript.strip())==0:
                    continue

                # create mp3 file for the clips
                clip_segment = wav_audio_file[time_start*1000:time_end*1000]  #pydub does things in milliseconds.
                clip_segment_file_name = generate_md5_hex(clip_segment) + ".mp3"
                clip_segment_file_path = os.path.join(self.dataset_clips_dir, clip_segment_file_name)
                clip_segment.export(clip_segment_file_path, format="mp3", parameters=["-acodec", "libmp3lame", "-ac", "1", "-ar", "32000", "-b:a", "48k"])
        
                # build up insert for database....
                t = {'transcript': transcript, 'confidence':confidence, 'start_time':time_start, 'end_time':time_end, 'model_name': self.speech_to_text.wav2vec2_model_path}
                t.setdefault("audio_source_id", audio_file["audio_id"])
                t.setdefault("clip_id", clip_segment_file_name)

                # lang detect on transcript:
                languageprediction = cld3.get_language(transcript)

                #
                t.setdefault("language", languageprediction.language)
                t.setdefault("language_isreliable", languageprediction.is_reliable)
                t.setdefault("language_probability", languageprediction.probability)

                # further processing possible.
                t.setdefault("duration", time_end - time_start)
      
                #
                transcriptions.append(t)

            #
            tqdm.write("Transcribed in {} seconds.".format(time.time() - start_time))

            #
            if len(transcriptions)>0:
                self.corpus_database.add_clips(transcriptions)
            
            #
            Path(destination_wav_file_path).unlink()
            tsv_file_path, tsv_good_file_path = self.export_all_transcripts_to_tsv()

            tsv_dedup_file_path = self.deduplicate_transcripts_export(tsv_good_file_path)

            tqdm.write(get_summary(tsv_file_path))
            tqdm.write(get_summary(tsv_good_file_path))
            tqdm.write(get_summary(tsv_dedup_file_path))



    def export_all_transcripts_to_tsv(self):
        df_clips = self.corpus_database.get_clips(self.speech_to_text.wav2vec2_model_path)
        tsv_file_name_base = self.speech_to_text.wav2vec2_model_path.replace("/","_")

        tsv_file_path = os.path.join(self.dataset_root_dir, tsv_file_name_base + "_clips.tsv")

        df_clips.to_csv(tsv_file_path, index=False, sep='\t')

        tsv_good_clips_file_path = os.path.join(self.dataset_root_dir, tsv_file_name_base + "_clips_good_cy.tsv") 
        df_good_clips_cy = self.corpus_database.get_good_clips(0.5, "cy", self.speech_to_text.wav2vec2_model_path)
        df_good_clips_cy.to_csv(tsv_good_clips_file_path , index=False, sep='\t')

        return tsv_file_path, tsv_good_clips_file_path
    

    def deduplicate_transcripts_export(self, tsv_good_file_path):
        df = pd.read_csv(tsv_good_file_path, sep='\t', header=0)
        df.drop_duplicates(subset=['clip_id'], keep='first', inplace=True)

        tsv_good_file = Path(tsv_good_file_path)
        tsv_dedup_file_name = tsv_good_file.stem + "_deduplicated_inprogress" + tsv_good_file.suffix
        tsv_dedup_abs_file_path = os.path.join(tsv_good_file.parent, tsv_dedup_file_name)
        df.to_csv(tsv_dedup_abs_file_path, index=False, sep='\t')

        return tsv_dedup_abs_file_path


    def iterate_downloads_folder(self):          
        for mp3_file in Path(self.downloads_root_dir).rglob("*.mp3"):
          yield mp3_file.absolute().as_posix()

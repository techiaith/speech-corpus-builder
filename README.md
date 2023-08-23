# Speech Corpus Builder

The scripts in this directory can be used to create a speech corpus of Welsh and English speech from YouTube, but could be 
adapted to other languages and maybe other video hosting websites.


## Downloading from YouTube

The package uses the popular [youtube-dl](https://github.com/ytdl-org/youtube-dl) command line utility. The program has raised questions on legality and piracy. You should check the licensing of each channel and/or video before including into your attempts at building a speech corpus from YouTube. Unless a Creative
Commons license is displayed on the corresponding pages on the YouTube website, then downloading could be considered copyright infringement. Therefore file `scripts/python/youtube_channels.txt` should contain channel sources with acceptable licensing.

However, these scripts will only store the audio and the meta-data for each downloaded video. The video content is filtered and removed. Each run of the scripts download videos not previously downloaded. 

N.B. at the moment, any associated transcript, or timed texts, files are not downloaded since we don't expect there to be many available for Welsh speech. 


## Speech Corpus Building Process

Once downloaded and the audio stored, voice activation detection is used to segment the entire audio into clips. Each clip is transcribed with a suitable ASR from HuggingFace models repo (at the moment a bilingual English-Welsh wav2vec2 model). The timings from transcripts are further used to keep each clip length to a maximum of 15 seconds. Each clips is stored as an mp3 file audio file with its filename and transcript kept in a row in a tab seperated file. `clips.tsv`.

Automatic trancripts will not be perfect which additional processing is conducted so as to identify transcriptions that are of higher quality as well as to detect language. This involves selecting transcripts with a confidence score higher than 50% by the acoustic model's CTC with also a 100% confident classification by the Google Common Language Detection (v3). 

Filtered clips and transcript may be useful for weak supervise learning. 

In the meantime, most, if not all, speech audio from clips may be useful for pre-training (e.g. wav2vec2 encoders). 


## Getting Started

You will need a Linux machine with docker installed. You don't necessarily need a GPU for inference by ASR models. But it does make the build process a lot quicker. 
Add your choice of channels from YouTube into a new `.scripts/python/youtube_channels.txt` file. 

For example, if you wanted to download all videos from https://www.youtube.com/@techiaith , then enter `techiaith` into a line of its own in `scripts/python/youtube_channels.txt`. If the channel contains streams (i.e. there is a 'Live' tab on its YouTube home page) then add `/streams` to the channel name in a new line. 

To fire up the docker container and run the script..

```
$ make
$ make run
# cd /corpus-builder/python
# python3 build.py
```

You'll see every YouTube video contained in your choice of channels being downloaded and transcribed. All downloaded audio, generated clips and transcriptions are contained in the container's  `/data/` directory which is also mapped to the `data` directory of your cloned repo. 


## Example Output

After the scripts have completed downloading all new channel audio content, it segment and transcribe each in turn, giving an update as to the total number of hours for each language (English and Welsh at the moment)

```
/data/welsh-youtube-corpus/downloads/digitalhealthandcarewales/vUxUOws1aKc__DHCW_Public_Board_Meeting_-_27_July_2023_English.mp3, duration 10493.887 seconds.
Transcribed in 305.73357033729553 seconds.

Duration of /data/welsh-youtube-corpus/dataset/techiaith_wav2vec2-xlsr-ft-en-cy_clips.tsv : 3287:19:02
Duration of cy only : 967:16:20 from 839593 clips
Duration of en only : 1848:33:27 from 1785424 clips

Duration of /data/welsh-youtube-corpus/dataset/techiaith_wav2vec2-xlsr-ft-en-cy_clips_good_cy.tsv : 25:30:23
Duration of cy only : 25:30:23 from 27969 clips
Duration of en only : 0:00:00 from 0 clips

Duration of /data/welsh-youtube-corpus/dataset/techiaith_wav2vec2-xlsr-ft-en-cy_clips_good_cy_deduplicated_inprogress.tsv : 25:14:14
Duration of cy only : 25:14:14 from 27715 clips
Duration of en only : 0:00:00 from 0 clips
```

You will find under `/data/welsh-youtube-corpus` (todo - change the name and remove 'Welsh') 

- sub-directories under `downloads` for each channel containing the audio of each video
- the corpus built as a collection of TSV files with transcripts and meta data along with a clips sub-directory. This is a format that's conveniant for pretraining and/or fine-tuning of ASR models from the HuggingFace models hub. 
- a sqlite database of all transcripts and durations. This may be useful for analysing and summing up the outputs of the corpus builder and/or creating custom TSV files.  

Note that there are three versions of TSV files - 

 - `<model_name>_clips.tsv` all results when using a particular model for transcribing
 - `<model_name>_clips_good.tsv` - all results filtered to those with higher confidence scores. 
 - `<model_name>_clips_deduplicated.tsv` - as filterd results but duplicate sound clips and transcriptions removed.
  
  
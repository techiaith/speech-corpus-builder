from youtube_corpus_builder import youtube_corpus

def main():
    
    ## download any new audio..
    ytc = youtube_corpus(corpus_root_dir="/data/welsh-youtube-corpus")

    with(open("youtube_channels.txt", 'r', encoding="utf-8")) as channels_list:
         for line in channels_list.readlines():
             if line.startswith("#"):
                 continue

             channel_name=line.strip()
             print (channel_name)
             ytc.download_channel(channel_name=channel_name)
    
    ## insert or update downloads details to database..
    ytc.dbimport_all_downloads()

    ## transcribe..
    ytc.create_transcribed_clips()

    ## export tsv
    ytc.export_all_transcripts_to_tsv()



if __name__ == "__main__":
    main()

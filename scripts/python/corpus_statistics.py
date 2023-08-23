import pandas as pd

from argparse import ArgumentParser, RawTextHelpFormatter


DESCRIPTION = """

(c) Prifysgol Bangor University

"""

def convert(ts):
    seconds=(ts)%60
    minutes=(ts/(60))%60
    hours=(ts/(60*60))

    return "%d:%02d:%02d" % (hours, minutes, seconds)


def language_duration(df, language):
    def duration_info(df, description):
        dfLangDuration = df['duration']
        duration = dfLangDuration.sum()
        totalClips = dfLangDuration.shape[0] 
        return "Duration of {} : {} from {} clips\n".format(description, convert(duration), totalClips)
    
    #
    dfLang = df.loc[df['language'] == language]
    lang_summary = duration_info (dfLang, language + " only")
    
    ## @todo - needs to be more generic / parameterised
    #dfLangWithConfidence = dfLang.loc[df['confidence'] > 0.5]
    #lang_summary += duration_info (dfLangWithConfidence, language + " with confidence 0.5")

    return lang_summary


def get_summary(corpus_csv_file):
    df = pd.read_csv(corpus_csv_file, sep='\t', header=0)
    #df["confidence"] = df["confidence"].astype('float64')

    #
    dfDuration = df['duration']
    
    #
    duration = dfDuration.sum()
    summary = "Duration of {} : {}".format(corpus_csv_file, convert(duration))
    summary += "\n"
    
    #
    summary += language_duration(df, "cy")
    summary += language_duration(df, "en")
    summary += "\n\n"
    
    return summary


def main(corpus_csv_file, **args):
    print (get_summary(corpus_csv_file))


if __name__ == "__main__":    
    parser = ArgumentParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter) 

    parser.add_argument("--csvfile", dest="corpus_csv_file", required=True)
    
    parser.set_defaults(func=main)
    args = parser.parse_args()
    args.func(**vars(args))

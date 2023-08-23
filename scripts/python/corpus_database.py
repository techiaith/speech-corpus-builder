import os
import sqlite3

import pandas as pd

from tqdm import tqdm

class corpus_database:


    def __init__(self, corpus_root_dir):
        os.makedirs(corpus_root_dir, exist_ok=True)
        self.conn = sqlite3.connect(os.path.join(corpus_root_dir, 'corpus.db'))
        self.conn.row_factory = sqlite3.Row
    
        #
        self.conn.executescript('''
            CREATE TABLE if not exists "audio_files" (
                "audio_id"              INTEGER PRIMARY KEY AUTOINCREMENT,
                "source_type"           TEXT,
                "source_id"             TEXT,
                "source_channel"        TEXT,
                "source_name"           TEXT,
                "source_url"            TEXT,
                "source_file_path"      TEXT,
                "date_added"            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        #
        self.conn.executescript('''
            CREATE TABLE if not exists "clips" (
                "audio_source_id"           INT,
                "clip_id"                   TEXT,
                "transcript"                TEXT, 
                "start_time"	            REAL,
                "end_time"	                REAL,                
                "duration"	                REAL,
                "model_name"                TEXT,
                "confidence"                REAL,
                "language"                  TEXT,
                "language_isreliable"       BOOLEAN,
                "language_probability"      REAL
            );
        ''')

        self.conn.commit()
        

    
    ## ---------------------------------------------------------
    def execute_script(self, sqlscript, params):
        cursor = self.conn.cursor()
        cursor.executemany(sqlscript, params)
        rc=cursor.rowcount
        cursor.close()
        self.conn.commit()
        return rc


    def execute_select(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        result=cursor.fetchall()
        cursor.close()
        self.conn.commit()
        return result


    ## ---------------------------------------------------------
    def get_all_audio_files_requiring_transcribing(self, model_name):
        sql_select = """
            SELECT audio_files.* FROM audio_files 
            LEFT JOIN (
                SELECT * FROM clips 
                WHERE model_name LIKE ?
            ) AS clips 
            ON clips.audio_source_id=audio_files.audio_id 
            WHERE clips.audio_source_id IS NULL;
        """
        return self.execute_select(sql_select, params=(model_name,))


    def get_audio_id(self, source_type, source_id):
        sql_select = """
            SELECT audio_id FROM audio_files 
            WHERE  source_type=?
            AND source_id=?
        """
        audio_source = self.execute_select(sql_select, (source_type, source_id))
        if len(audio_source)>0:
            return audio_source[0]["audio_id"]
        else:
            return 0    


    def get_clips(self, model_name):
        sql_select = """
            SELECT C.clip_id, C.transcript, C.start_time, C.end_time, C.duration, C.language, C.confidence, C.language_isreliable, C.language_probability,
                   A.source_type, A.source_id, A.source_channel, A.source_name, A.source_url  
            FROM clips AS C
            INNER JOIN audio_files AS A ON C.audio_source_id=A.audio_id
            WHERE C.model_name LIKE ?
        """
        return pd.read_sql(sql_select, self.conn, params=(model_name,))


    def get_good_clips(self, confidence, language, model_name):
        sql_select = """
            SELECT C.clip_id, C.transcript, C.start_time, C.end_time, C.duration, C.language, C.confidence, C.language_isreliable, C.language_probability,
                   A.source_type, A.source_id, A.source_channel, A.source_name, A.source_url  
            FROM clips AS C
            INNER JOIN audio_files AS A ON C.audio_source_id=A.audio_id
            WHERE C.language=?
            AND C.confidence>?
            AND C.language_isreliable=true
            AND C.language_probability=1.0 
            AND C.model_name LIKE ?
        """
        return pd.read_sql(sql_select, self.conn, params=(language, confidence, model_name))
    

    ## ---------------------------------------------------------
    def add_audio_source(self, source_type, source_id, source_channel, source_name, source_url, source_file_path):
        
        #
        audio_id = self.get_audio_id(source_type, source_id)
        if audio_id>0:
            #
            sql_update = """
                UPDATE audio_files
                SET source_channel=?,
                    source_name=?,
                    source_url=?,
                    source_file_path=? 
                WHERE audio_id=?
            """
            print ("U ", source_channel, source_id)
            self.execute_script(sql_update, [(source_channel, source_name, source_url, source_file_path, audio_id)])
            return audio_id
        else:
            sql_insert = """
                INSERT INTO audio_files (source_type, source_id, source_channel, source_name, source_url, source_file_path) 
                VALUES (?,?,?,?,?,?)
            """
            print ("I ", source_channel, source_id)
            self.execute_script(sql_insert,[(source_type, source_id, source_channel, source_name, source_url, source_file_path)]) 
            return self.get_audio_id(source_type, source_id)
    


    def add_clips(self, clips):
        #
        columns = ', '.join(clips[0].keys())
        placeholders = ':'+', :'.join(clips[0].keys())

        #
        sql = 'INSERT INTO clips (%s) VALUES (%s)' % (columns, placeholders)
        cursor = self.conn.cursor()
        cursor.executemany(sql, clips)
        rc=cursor.rowcount
        cursor.close()
        self.conn.commit()
        return rc

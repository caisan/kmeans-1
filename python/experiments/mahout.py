import sys
import os
import math
import time
import logging
import uuid
import datetime
import copy
import glob
import traceback
from string import Template

RESULT_DIR="results"
RESULT_FILE_PREFIX="mahout-"
HEADER = ("Run", "Input", "Number_Cluster", "Time Type", "Time", "Timestamp")
HEADER_CSV = ("%s;%s;%s;%s;%s;%s\n"%HEADER)
HEADER_TAB = ("%s\t%s\t%s\t\t%s\t%s\t%s\n"%HEADER)
NUMBER_REPEATS=5
INPUT_DATA_PATH="/data/input-judy/"
HDFS_INPUT="kmeans"
HDFS_OUTPUT="kmeans/output"
NUMBER_OF_CLUSTERS=500
ITERATIONS=10
#CHUNKSIZE={5000:4837888, 50000:482816, 500:48376832} #96 mappers
#CHUNKSIZE={5000:9675776, 50000:965632, 500:96753152} #48 mapper
CHUNKSIZE={5000:19351040, 50000:1931264, 500:193506304} #24 mapper

# Commands for the individual steps
MAHOUT_VECTOR_CONVERSION_CMD="HADOOP_CLASSPATH=/data/bin/mahout-distribution-0.8/mahout-core-0.8-job.jar; hadoop jar /data/kmeans/mahout/kmeans/target/kmeans-1.0-SNAPSHOT-jar-with-dependencies.jar"


MAHOUT_KMEANS_CMD=Template("/data/bin/mahout-distribution-0.8/bin/mahout kmeans --input $input --output "+ HDFS_OUTPUT + " --clusters " + os.path.join(HDFS_OUTPUT, "clusters") + " --numClusters $clusters --overwrite --outlierThreshold 0 --distanceMeasure org.apache.mahout.common.distance.EuclideanDistanceMeasure --convergenceDelta 0 --maxIter " + str(ITERATIONS))


""" Test Job Submission via BigJob """
if __name__ == "__main__":
    try:
        os.mkdir(RESULT_DIR)
    except:
        pass

        
    d =datetime.datetime.now()
    result_filename = RESULT_FILE_PREFIX + d.strftime("%Y%m%d-%H%M%S") + ".csv"
    f = open(os.path.join(RESULT_DIR, result_filename), "w")
    f.write(HEADER_CSV)
    for repeat_id in range(0, NUMBER_REPEATS):
        for filename in os.listdir(INPUT_DATA_PATH):
	    clusters = filename[filename.rfind("_")+1:filename.rfind("cluster")]
	    chunk_size=CHUNKSIZE[int(clusters)]
            print "Run kmeans with: " + str(filename) + " clusters: " + clusters + " Chunk Size: " + str(chunk_size)
            try:
                start = time.time()
                hdfs_path = os.path.join(HDFS_INPUT, os.path.splitext(filename)[0], "data.csv")
                os.system(MAHOUT_VECTOR_CONVERSION_CMD + " " + os.path.join(INPUT_DATA_PATH, filename) + " " + hdfs_path)
                end_conversion = time.time()
                result_tuple = (repeat_id, str(os.path.splitext(filename)[0]), str(clusters), "Preparation", end_conversion-start, datetime.datetime.today().isoformat(), chunk_size)
                line =  ("%s;%s;%s;%s;%s;%s;%s;\n"%(result_tuple))  
                f.write(line)
                f.flush()

		hdfs_final_path = os.path.join(HDFS_INPUT, os.path.splitext(filename)[0], "data.mvector")
		os.system("hadoop fs -D dfs.replication=4 -Ddfs.block.size="+ str(chunk_size) + " -cp " + hdfs_path + " " + hdfs_final_path)
		os.system("hadoop fs -rm " + hdfs_path)

                mahout_cmd = MAHOUT_KMEANS_CMD.substitute(input=hdfs_final_path, clusters=clusters)
                print "Run: %s"%mahout_cmd
                os.system(mahout_cmd)
                end = time.time()
                result_tuple = (repeat_id, str(os.path.splitext(filename)[0]), str(clusters), "KMeans", end-end_conversion, datetime.datetime.today().isoformat(), chunk_size)
                line =  ("%s;%s;%s;%s;%s;%s;%s;\n"%(result_tuple))  
                f.write(line)
                f.flush()
            
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print "Run " +str(repeat_id)+ " failed: " + str(exc_value)
                print "*** print_tb:"
                traceback.print_tb(exc_traceback, limit=1, file=sys.stderr)
                print "*** print_exception:"
                traceback.print_exception(exc_type, exc_value, exc_traceback,
                                           limit=2, file=sys.stderr)
            time.sleep(10)

    f.close()
    print("Finished run")

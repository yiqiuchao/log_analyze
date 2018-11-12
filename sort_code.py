#!/usr/bin/env python

import sys
import re
import csv

if len(sys.argv) < 3:
    print "Please input filename and version(U17 or U18)."
    exit(1)

inputfile = sys.argv[1]
if sys.argv[2] == "U17":
    version  = "1.466"
elif sys.argv[2] == "U18":
    version  = "1.481"
else:
    print "Invalid version, should be U17 or U18."
    exit(1)

inputm = []
with open(inputfile, "rb") as f:
    reader = csv.reader(f, delimiter=",")
    for row in reader:
        inputm.append(row)

# 0x0f0f0f0f
lines_0x0f = []
num_0x0f = 0
# 0x00000000
lines_0x00 = []
num_0x00 = 0
# 0x03&0x01
lines_0x03 = []
num_0x03 = 0
re_0x03 = "^0x0[0,1,3]0[0,1,3]0[0,1,3]0[0,1,3]$"
# 0x0b&0x07
lines_0x0b07 = []
num_0x0b07 = 0
re_0x07 = "^0x0[0,1,3,7]0[0,1,3,7]0[0,1,3,7]0[0,1,3,7]$"
# others
lines_other = []
num_others = 0

for line in inputm:
    if len(line) >= 6 and version in line[1]:
        code = line[0]
        num  = int(line[2].replace(',', ''))
        if code == "0x0f0f0f0f":
            lines_0x0f.append(line)
            num_0x0f = int(num_0x0f) + num
        elif code == "0x00000000":
            lines_0x00.append(line)
            num_0x00 = int(num_0x00) + num
        # 0x00000000 is counted already.
        elif re.match(re_0x03, code):
            lines_0x03.append(line)
            num_0x03 = int(num_0x03) + num
        # 0x00000000 and 0x03&0x01 are counted already.
        elif code == "0x0b0b0b0b" or re.match(re_0x07, code):
            lines_0x0b07.append(line)
            num_0x0b07 = int(num_0x0b07) + num
        else:
            lines_other.append(line)
            num_others = num_others + num

sum = num_0x0f+num_0x00+num_0x03+num_0x0b07+num_others

if sum == 0:
    print "No records to save."
    exit(0)


csvfile = "out.csv"
print "Save result to %s\n" % csvfile
summarize = ""
summarize += ("0x0f0f0f0f = %10d,\t" % num_0x0f) + "{:>6.02%}".format(float(num_0x0f)/sum) + "\n"
summarize += ("0x00000000 = %10d,\t" % num_0x00) + "{:>6.02%}".format(float(num_0x00)/sum) + "\n"
summarize += ("0x03010000 = %10d,\t" % num_0x03) + "{:>6.02%}".format(float(num_0x03)/sum) + "\n"
summarize += ("0x0b070301 = %10d,\t" % num_0x0b07) + "{:>6.02%}".format(float(num_0x0b07)/sum) + "\n"
summarize += ("othercodes = %10d,\t" % num_others) + "{:>6.02%}".format(float(num_others)/sum) + "\n"
print summarize

with open(csvfile, "w") as output:
    print >> output, summarize

    writer = csv.writer(output, lineterminator='\n')
    writer.writerows(lines_0x0f)
    writer.writerows(lines_0x00)
    writer.writerows(lines_0x03)
    writer.writerows(lines_0x0b07)
    writer.writerows(lines_other)

# with open(out_file, "w") as f:
#     print >> f, "Save result to %s" % out_file
    # print >> f, "0x0f0f0f0f = %d,\t %f" % (num_0x0f, float(num_0x0f)/sum)
    # print >> f, "0x00000000 = %d,\t %f" % (num_0x00, float(num_0x00)/sum)
    # print >> f, "0x03000000 = %d,\t %f" % (num_0x03, float(num_0x03)/sum)
    # print >> f, "0x0b000000 = %d,\t %f" % (num_0x0b07, float(num_0x0b07)/sum)
    # print >> f, "others     = %d,\t %f" % (num_others, float(num_others)/sum)
#     print >> f, "#############################################"
#     print >> f, lines_0x0f
#     print >> f, lines_0x00
#     print >> f, lines_0x03
#     print >> f, lines_0x0b07
#     print >> f, lines_other
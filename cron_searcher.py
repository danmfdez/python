#!/usr/bin/env python
# -*- coding: utf-8 -*- 

'''

Gets the list of cron lines to be executed between two dates.

Author: Daniel Muñoz [sinmaker(at)gmail(dot)com]

'''

import sys
import os
import argparse
import datetime
import calendar
import re


# Expands a cron time field to list of values
def cronToList(var, min, max, expand=True):
    varList = []

    var1, var2 = (var.split(',', 1) + [False]*1)[:2]

    if re.match("(\*(/\d+)?|\d+(-\d+(/\d+)?)?)", var1):
        if re.match("^\*/\d+$", var1):              #*/12
            interval = int(var1.split('/')[1])
            for i in range(min, (max + 1)/ interval):
                varList.append(i * interval)
        elif var1 == "*":                           #*
            if expand:
                for i in range(min, max + 1):
                    varList.append(i)
            else:
                varList = '*'
        elif var1.isdigit():                        #2
            varList.append(int(var1))
        elif re.match("^\d+-\d+\/\d+$", var1):      #14-22/2
            rang = var1.split('/')[0]
            interval = int(var1.split('/')[1])
            for i in range(int(rang.split('-')[0]) / interval, (int(rang.split('-')[1]) + interval) / interval):
                varList.append(i * interval)
        elif re.match("^\d+-\d+$", var1):           #12-15
            for i in range(int(var1.split('-')[0]), int(var1.split('-')[1]) + 1):
                varList.append(i)

    if var2:
        varList += cronToList(var2, min, max, expand)

    return varList


# Extracts time information from a crontab line
def processLine(line):
    minutes = cronToList(line.split(' ')[0], 0, 59)
    hours = cronToList(line.split(' ')[1], 0, 23)
    days_month = cronToList(line.split(' ')[2], 1, 31, False)
    months = cronToList(line.split(' ')[3], 1, 12)
    days_week = cronToList(line.split(' ')[4], 0, 7, False)
    command = line.split(' ', 5)[5]

    return minutes, hours, days_month, months, days_week, command


# Extracts time information from a crontab line (in special lines)
def processSpecialLine(line):
    time, comm = line.split(' ', 1)

    if time == "@hourly":
        minutes, hours, days_month, months, days_week, command = processLine("0 * * * * " + comm)
    elif time == "@daily" or time == "@midnight":
        minutes, hours, days_month, months, days_week, command = processLine("0 0 * * * " + comm)
    elif time == "@weekly":
        minutes, hours, days_month, months, days_week, command = processLine("0 0 * * 0 " + comm)
    elif time == "@monthly":
        minutes, hours, days_month, months, days_week, command = processLine("0 0 1 * * " + comm)
    elif time == "@yearly" or time == "@annually":
        minutes, hours, days_month, months, days_week, command = processLine("0 0 1 1 * " + comm)
    else:
        minutes = hours = days_month = months = days_week = command = ""

    return minutes, hours, days_month, months, days_week, command


# Creates a list of days of the month to coincide with a day of the week.
def findWeekDays(weekday, month, year):
    oneday = datetime.timedelta(days=1)
    oneweek = datetime.timedelta(days=7)
    wday = (weekday - 1) % 7

    start = datetime.date(year=year, month=month, day=1)
    while start.weekday() != wday:
        start += oneday
    days = []
    while start.month == month:
        days.append(start.day)
        start += oneweek

    return days


# Checks if date is in correct format 'YYYYmmddHHMM'
def dateFormat(date):
    if date.isdigit() and len(date) == 12 and 1 <= int(date[4:6]) <= 12 and 1 <= int(date[6:8]) <= 31 \
            and int(date[8:10]) < 24 and int(date[10:]) < 60:
        return date[:4], date[4:6], date[6:8], date[8:10], date[10:], "00"
    else:
        print "Error in format date: 'YYYYmmddHHMM' (year, month 01-12, day 01-31, hour 00-23, minute 00-59)"
        sys.exit(2)


# Converts input string in a correct date
def createDate(year, month, day, hour, minute, sec):
    try:
       return datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(sec))
    except ValueError:
        print 'Error:', year + '/' + month + '/' + day, hour + ':' + minute + ':' + sec + ', is not a valid date.'
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Two verbose levels')
    parser.add_argument('-f', '--file', nargs='+', dest='cron_file', required=True)
    parser.add_argument('-s', '--start-date', dest='start_Date', help='Start date in format "YYYYmmddHHMM"', required=True)
    parser.add_argument('-e', '--end-date', dest='end_Date', help='End date in format "YYYYmmddHHMM"', required=True)
    args = parser.parse_args()

    for file in args.cron_file:
        if not os.path.exists(file):
            print "File", file, "does not exist."
            sys.exit(1)

    # Validate correct format and date values
    sdate = createDate(*dateFormat(args.start_Date))
    edate = createDate(*dateFormat(args.end_Date))

    if sdate > edate:
        print "Error: The end date must be greater than the start date."
        sys.exit(1)

    matching_lines = []
    not_matching_lines = []
    not_cron_lines = []

    years = []
    for i in range(int(sdate.year), int(edate.year) + 1):
        years.append(i)

    for file in args.cron_file:
        with open(file, 'r') as content_file:
            for line in content_file:
                other_line = False

                # Filter cron lines
                if line[0] == "*" or line[0].isdigit():
                    minutes, hours, days_month, months, days_week, command = processLine(line)
                elif line[0] == "@":
                    minutes, hours, days_month, months, days_week, command = processSpecialLine(line)
                else:
                    if not line == "\n":
                        not_cron_lines.append(line)
                    continue

                not_matching_lines.append(line)

                for year in years:
                    for month in months:
                        max_days = calendar.monthrange(year, month)[1]

                        # Choose between days of the month and days of the week
                        if days_month != '*' and days_week != '*':
                            days_in_this_month = [i for i in days_month if i <= max_days]
                            for i in days_week:
                                days_in_this_month += findWeekDays(i, month, year)
                            days_in_this_month = sorted(set(days_in_this_month))
                        elif days_week == '*':
                            if days_month == '*':
                                days_in_this_month = cronToList(days_month, 1, max_days)
                            else:
                                days_in_this_month = [i for i in days_month if i <= max_days]
                        else:
                            days_in_this_month = []
                            for i in days_week:
                                days_in_this_month += findWeekDays(i, month, year)
                            days_in_this_month = sorted(set(days_in_this_month))

                        for day in days_in_this_month:
                            for hour in hours:
                                for minute in minutes:
                                    date = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
                                    if sdate <= date <= edate:
                                        other_line = True
                                        matching_lines.append(line)
                                        del not_matching_lines[-1]
                                        break
                                if other_line:
                                    break
                            if other_line:
                                break
                        if other_line:
                            break
                    if other_line:
                        break

    sys.stdout.write("MATCHING CRON LINES:\n")
    for i in matching_lines:
        sys.stdout.write(i)

    if args.verbose > 0:
        sys.stdout.write("\nNON-MATCHING CRON LINES:\n")
        for i in not_matching_lines:
            sys.stdout.write(i)
    if args.verbose > 1:
        sys.stdout.write("\nNOT CRON LINES:\n")
        for i in not_cron_lines:
            sys.stdout.write(i)



if __name__ == '__main__':
    main()

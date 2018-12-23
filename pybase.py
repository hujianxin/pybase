import re
import os
import logging
import subprocess

logging.basicConfig()


class PyBaseException(Exception):
    def __init__(self, message):
        self.message = message


class Cell(object):
    def __init__(self, row, column, timestamp, value):
        self.__row = row
        self.__column = column
        self.__timestamp = timestamp
        self.__value = value

    @property
    def row(self):
        return self.__row

    @property
    def column(self):
        return self.__column

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def value(self):
        return self.__value


class Status(object):
    def __init__(self, servers, dead, average_load):
        self.__servers = servers
        self.__dead = dead
        self.__average_load = average_load

    @property
    def servers(self):
        return self.__servers

    @property
    def dead(self):
        return self.__dead

    @property
    def average_dead(self):
        return self.__average_load

    def __str__(self):
        return "{} servers, {} dead, {} average load".format(
            self.__servers, self.__dead, self.__average_load
        )


class Version(object):
    def __init__(self, version, revision, date_time):
        self.__version = version
        self.__revision = revision
        self.__date_time = date_time

    @property
    def version(self):
        return self.__version

    @property
    def revision(self):
        return self.__revision

    @property
    def date_time(self):
        return self.__date_time

    def __str__(self):
        return "{}, {}, {}".format(self.__version, self.__revision, self.__date_time)


class PyBase(object):
    def __init__(self, shell):
        self.__shell = shell
        if not os.path.exists(shell):
            raise PyBaseException("Wrong hbase shell path")
        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel(logging.DEBUG)

    def __do(self, cmd):
        query = subprocess.Popen(["echo", cmd], stdout=subprocess.PIPE)
        result = subprocess.Popen(
            [self.__shell, "shell"], stdin=query.stdout, stdout=subprocess.PIPE
        )
        query.stdout.close()
        output = []
        line = result.stdout.readline()
        while line:
            output.append(line.strip())
            line = result.stdout.readline()
        result.stdout.close()
        return output

    def do(self, cmd):
        return self.__do(cmd)

    # -------------general------------- #
    def status(self):
        pattern = re.compile(
            r"(\d+?) servers, (\d+?) dead, (\d+?)\.(\d+?) average load"
        )
        result = self.__do("status")
        for item in result:
            matched_item = pattern.match(item)
            if matched_item:
                servers = int(matched_item.group(1))
                dead = int(matched_item.group(2))
                average_load_1 = matched_item.group(3)
                average_load_2 = matched_item.group(4)
                average_load = float("{}.{}".format(average_load_1, average_load_2))
                return Status(servers, dead, average_load)
        raise PyBaseException("no result")

    def version(self):
        pattern = re.compile(
            r"(.*?), (.*?), (\S\S\S \S\S\S \d\d \d\d:\d\d:\d\d \w+? \d\d\d\d)"
        )
        cmd = "version"
        self.__log_execute(cmd)
        result = self.__do(cmd)
        for item in result:
            matched_item = pattern.match(item)
            if matched_item:
                return Version(
                    matched_item.group(1), matched_item.group(2), matched_item.group(3)
                )
        raise PyBaseException("no result")

    def whoami(self):
        cmd = "whoami"
        self.__log_execute(cmd)
        result = self.__do(cmd)
        matched = False
        for item in result:
            if item == "whoami":
                matched = True
                continue
            if matched:
                return item
        raise PyBaseException("no result")

    # -------------dml------------- #
    def scan(
        self,
        table,
        columns=None,
        limit=None,
        startrow=None,
        endrow=None,
        time_range=None,
        reversed=False,
        debug=False,
        filter=None,
    ):
        output = self.__do("")
        print("Output: ", output)

    def get(
        self,
        table,
        rowkey,
        column=None,
        timestamp=None,
        timerange=None,
        versions=None,
        filter=None,
    ):
        base_cmd = "get '{}', '{}'".format(table, rowkey)
        if column or timestamp or timerange or versions or filter:
            base_cmd += ", {"
        if column and isinstance(column, str):
            base_cmd += "COLUMN => '{}', ".format(column)
        elif column and isinstance(column, list):
            base_cmd += "COLUMN => {}, ".format(column)
        elif column:
            raise PyBaseException("Wrong column format")
        if timestamp:
            base_cmd += "TIMESTAMP => {}, ".format(timestamp)
        if timerange:
            base_cmd += "TIMERANGE => {}, ".format(timerange)
        if versions:
            base_cmd += "VERSIONS => {}, ".format(versions)
        if filter:
            base_cmd += 'FILTER => "{}", '.format(filter)
        if "{" in base_cmd:
            length = len(base_cmd)
            base_cmd = base_cmd[0 : length - 2] + "}"
        self.__log_execute(base_cmd)
        execute_result = self.__do(base_cmd)
        self.__logger.debug("Executed result: {}".format(execute_result))

        start_pattern = re.compile(r"COLUMN\s+?CELL")
        stop_pattern = re.compile(r"\d+? rows\(s\) in \d+?\.\d+? seconds")
        pattern = re.compile(r"(.*?)\s+?column=(.*?), timestamp=(.*?), value=(.*?)")

        start = False
        result = []
        for item in execute_result:
            if not start:
                if start_pattern.match(item):
                    self.__logger.info("Getting started at: {}".format(item))
                    start = True
                continue
            if stop_pattern.match(item):
                self.__logger.info("Getting stopped at: {}".format(item))
                break
            matched_item = pattern.match(item)
            if matched_item:
                cell = Cell(
                    matched_item.group(1),
                    matched_item.group(2),
                    matched_item.group(3),
                    matched_item.group(4),
                )
                result.append(cell)
        return result

    def put(self):
        pass

    def __log_execute(self, message):
        self.__logger.info("Executing command: {}".format(message))

    # -------------tools-------------
    # -------------ddl-------------
    # -------------namespace-------------
    # -------------snapshot-------------
    # -------------replication-------------
    # -------------quotas-------------
    # -------------security-------------
    # -------------visibility labels-------------

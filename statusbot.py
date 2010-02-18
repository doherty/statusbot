#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Mike.lifeguard <mike.lifeguard@gmail.com>
# License: GPL

import MySQLdb
import os
import random
import re
import string
import sys
import time

# The config file for this bot - must be located at ./config.py
# Copy and customize config.py.example
import config

# Needs python-irclib
from ircbot import SingleServerIRCBot
from irclib import nm_to_n

# DB data
SQLuser=config.dbuser
SQLpassword=config.dbpass
SQLhost=config.dbhost
SQLdb=config.dbdb

# Common queries
queries = {
    'listenchannels' : ('select l_channel from listen'),
    'getproblems'    : ('select s_service,s_state,s_ok from '
                        'status where s_ok is false'),
    'getok'          : ('select s_service,s_state,s_ok from '
                        'status where s_ok is true'),
    'getstatuses'    : ('select s_service,s_state,s_ok from status'),
    'setallclear'    : ('update status set s_state="OK",s_ok=true')
    }

def query(sqlquery, one=True):
    """
    Run a query that just gets data from the database.

    If you're using more than one column, set call this with one=False.

    """
    db = MySQLdb.connect(db=SQLdb, host=SQLhost,
                         user=SQLuser, passwd=SQLpassword)
    cursor = db.cursor()
    cursor.execute(sqlquery)
    db.close()
    res = list(cursor.fetchall())
    list.sort(res)
    if one:
        res2 = []
        for i in res:
            if i[0] is not None:
                res2 += [i[0]]
        return res2
    else: return res

def modquery(sqlquery):
    """
    Run a query that commits to the database.

    """
    db = MySQLdb.connect(db=SQLdb, host=SQLhost,
                         user=SQLuser, passwd=SQLpassword)
    cursor = db.cursor()
    cursor.execute(sqlquery)
    db.commit()
    db.close()

class FreenodeBot(SingleServerIRCBot):
    """
    Create a bot that connects to the freenode IRC network.

    Technically, it can connect to anything, but in statusbot.py it
    connects to freenode, so we call it that. Takes no parameters.

    """
    def __init__(self):
        self.server = config.server
        self.port = config.port
        self.channel = config.channel
        self.nickname = config.nick
        self.password = config.password
        self.listenchannels = query(queries['listenchannels'])
        self.quiet = False
        self.notify = True
        self.dorandmess = False
        self.randmessage = config.randmessage
        self.listen = True
        self.docurl = config.docurl
        self.proxynicks = config.proxynicks
        SingleServerIRCBot.__init__(
            self, [(self.server, self.port,
                    # We can overload this tuple to send a server password
                    "%s:%s" % (self.nickname, self.password))],
            self.nickname, self.nickname)

    def on_error(self, c, e):
        """
        Called when some kind of IRC error happens.

        WTF does that mean?!

        """
        print e.target()
        self.die()

    def on_nicknameinuse(self, c, e):
        """
        Called when the server tells us our nick is already in use.

        We attempt to ghost the nick and acquire it.

        """
        # Probably unnecessary, since sending a server password will
        # log us in regardless whether we have our main nick or not.
        c.nick(c.get_nickname() + "_")
        time.sleep(2) # latency problem?
        c.privmsg("NickServ","GHOST %s %s" % (self.nickname, self.password))
        c.nick(self.nickname)
        time.sleep(2) # latency problem?
        c.privmsg("NickServ","IDENTIFY %s" % self.password)

    def on_welcome(self, c, e):
        """
        Called when the server welcomes us after successfully connecting.

        We log the fact, and identify to nickserv.

        """
        print "Connected to server successfully"
        # Probably unnecessary, since sending a server password will
        # log us in regardless whether we have our main nick or not.
        c.privmsg("NickServ",'IDENTIFY %s' % self.password)
        time.sleep(4) # Let identification succeed before joining channels
        c.join(self.channel)
        if self.listen and self.listenchannels:
            for chan in self.listenchannels:
                c.join(chan)

    def on_ctcp(self, c, e):
        """
        Called when the bot recieves a CTCP message.

        We only respond to:
         * VERSION, with a short string describing the bot
         * PING, if a timestamp is provided (the server requires it)
         * SOURCE, with a URL to documentation for the bot

        """
        if e.arguments()[0] == "VERSION":
            c.ctcp_reply(nm_to_n(e.source()),
                         "Bot for providing status information on %s"
                         % self.channel)
        elif e.arguments()[0] == "PING":
            if len(e.arguments()) > 1:
                c.ctcp_reply(nm_to_n(e.source()),
                             "PING %s" % e.arguments()[1])
        elif e.arguments()[0] == "SOURCE":
            c.ctcp_reply(nm_to_n(e.source()), self.docurl)

    def on_privmsg(self, c, e):
        """
        Called when the bot recieves a private message.

        We parse the message, and try to find a command. Commands
        are only passed along to do_command if the user is voiced
        or opped in the main channel. Replies are sent back to
        the user by PM.

        """
        timestamp = time.strftime('%d.%m.%Y %H:%M:%S',
                                  time.localtime(time.time()))
        nick = nm_to_n(e.source())
        target = nick # If they did the command in PM, keep replies in PM
        text = e.arguments()[0]
        a = text.split(':', 1)
        print "[%s] <%s/%s> %s" % (timestamp, "PM", nick, a)
        if a[0] == self.nickname:
            if len(a) == 2:
                # Now we don't need to .lower() everywhere else
                command = a[1].strip().lower()
                if self.channels[self.channel].is_voiced(nick) \
                         or self.channels[self.channel].is_oper(nick):
                    try:
                        self.do_command(e, command, target)
                    except CommanderError, e:
                        print 'CommanderError: %s' % e.value
                        self.msg('\x0305Error:\x0F %s. '
                                 'See \x0302%s\x0F for the proper syntax'
                                 % (e.value, self.docurl), nick)
                    except:
                        print 'Error: %s' % sys.exc_info()[1]
                        raise # Re-raise the last exception
                elif command == 'test': # Safe-ish to let them do this
                    self.do_command(e, command, target)
                elif command == 'help': # Safe-ish to let them do this
                    self.do_command(e, command, target)
                else:
                    self.msg('Sorry, you need to be voiced in %s'
                             'to give the bot commands.' % self.channel, nick)

    def on_pubmsg(self, c, e):
        """
        Called when the bot recieves a message in a channel.

        We parse the message, and try to find a command. Commands
        are only passed along to do_command if the user is voiced
        or opped in the main channel. Replies are sent back to
        the user in the channel, with some exceptions:
         * help is replied to in PM
         * ??

        """
        #self.randmess() # Maybe we'll send a message, maybe we won't...
        timestamp = time.strftime('%d.%m.%Y %H:%M:%S',
                                  time.localtime(time.time()))
        nick = nm_to_n(e.source())
        # If they issued the command in a channel,
        # replies should go to the channel
        target = e.target()
        text = e.arguments()[0]
        a = text.split(':', 1)
        if a[0] == self.nickname:
            print '[%s] <%s/%s> %s' % (timestamp, e.target(), nick, text)
            if len(a) == 2:
                # Now we don't need to .lower() everywhere else
                command = a[1].strip().lower()
                if self.channels[self.channel].is_voiced(nick) \
                         or self.channels[self.channel].is_oper(nick):
                    try:
                        self.do_command(e, command, target)
                    except CommanderError, e:
                        print 'CommanderError: %s' % e.value
                        self.msg('\x0305Error:\x0F %s. '
                                 'See \x0302%s\x0F for the proper syntax'
                                 % (e.value, self.docurl), nick)
                    # This bare except causes problems when a
                    # ServerNotConnectedError is raised :\
                    # Not quite sure what to do here...
                    except:
                        print 'Error: %s' % sys.exc_info()[1]
                        self.msg('Unknown internal error: %s'
                                 % sys.exc_info()[1], target)
                        raise
                elif command == 'test': # Safe-ish to let them do this
                    self.do_command(e, command, target)
                elif command == 'help': # Safe-ish to let them do this
                    self.do_command(e, command, target)
                else:
                    self.msg('Sorry, you need to be voiced in %s '
                             'to give the bot commands.' % self.channel, nick)
        else:
            # If it's a message we care about!
            # Pretty this up!
            if self.startswitharray(text.lower(), ["!log", "!status"]):
                channel = e.target()
                if channel != self.channel:
                    nick = nm_to_n(e.source())
                    text = re.sub("^(!log|!status)", "", text).strip()
                    if nick in self.proxynicks: # Make it clearer who did what
                        nick = text.split(" ", 1)[0].strip()
                        text = text.split(" ", 1)[1].strip()
                    print '[%s] <%s/%s> %s' % (timestamp, channel, nick, text)
                    out = "\x0303<%s>\x0F %s" % (nick, text)
                    # Always send !log echoes to the main channel
                    self.msg(out, self.channel)
                else:
                    pass # Someone is probably thinking they're very clever

    def on_topic(self, c, e):
        """
        Called whenever the bot recieves a message saying the /topic changed.

        We log the fact, and pass it along to the main channel, unless
        it happened in the main channel (in which case repeating that
        is just spammy).

        """
        timestamp = time.strftime('%d.%m.%Y %H:%M:%S',
                                  time.localtime(time.time()))
        nick = nm_to_n(e.source())
        channel = e.target()
        if channel != self.channel:
            topic = e.arguments()[0]
            channel = e.target()
            print '[%s] <%s/%s> %s' % (timestamp, channel, nick, topic)
            out = "\x0306New topic:\x0F %s" % topic
            # Always send /topic changes to the main channel
            self.msg(out, self.channel)
        else:
            pass # That's self.channel's topic changing

    def do_command(self, e, cmd, target=None):
        """
        Parse the given command, and send it off to do_X for actual doing.

        The die command is implemented in this method, and not in its
        own do_die method.

        """
        print "do_command(self, e, %s, %s)" % (cmd, target)
        nick = nm_to_n(e.source())
        if not target:
            target = self.channel
        c = self.connection

        # On/Off
        if cmd == "quiet":
            if not self.quiet:
                self.msg("I'll be quiet :(", target)
                self.quiet=True
        elif cmd == "speak":
            if self.quiet:
                self.msg("Back in action :)", target)
                self.quiet=False
        elif cmd == "notify on":
            if not self.notify:
                self.msg("Notification on", target)
                self.notify=True
        elif cmd == "notify off":
            if self.notify:
                self.msg("Notification off", target)
                self.notify=False
        elif cmd == "randmsg on":
            if not self.randmess:
                self.msg("Message notification on", target)
                self.randmess=True
        elif cmd == "randmsg off":
            if self.randmess:
                self.msg("Message notification off", target)
                self.randmess=False

        # Listen
        elif cmd.startswith("listen"):
            # This one needs nick to avoid passing e
            self.do_listen(re.sub("^listen", "", cmd).strip(), target, nick)

        # Status
        elif cmd.startswith("status"):
            if cmd == "status":
                cmd = "status list all" # default output
            self.do_status(re.sub("^status", "", cmd).strip(), target)

        # Service
        elif cmd.startswith("service"):
            self.do_service(re.sub("^service", "", cmd).strip(), target)

        # Help
        elif cmd == "help":
            self.msg("My documentation is \x0302%s\x0F" % self.docurl, nick)

        # Test
        elif cmd == "test":
            self.msg("Yes, I'm alive. My documentation is \x0302%s\x0F"
                     % self.docurl, nick)

        # Huggle
        elif cmd.startswith("huggle"):
            who = cmd[6:].strip() # WTF?
            self.connection.action(self.channel, "huggles %s" % who)

        # Die
        elif cmd.startswith("die"):
            if self.channels[self.channel].is_oper(nick):
                text = cmd.split("die", 1)[1].strip()
                if not text:
                    quitmsg = "Goodbye, cruel world!"
                else:
                    quitmsg = text
                c.part(self.channel, ":" + quitmsg)
                if self.listen:
                    for chan in self.listenchannels:
                        self.connection.part(chan, ":" + quitmsg)
                self.connection.quit(":" + quitmsg)
                self.disconnect()
                c.quit()
                self.disconnect()
                # Exit from Python. This is implemented by raising the
                # SystemExit exception, so cleanup actions specified by
                # 'finally' clauses of try statements are honoured, and
                # it is possible to intercept the exit attempt at an
                # outer level.
                sys.exit()
            else:
                if not self.quiet:
                    self.msg("You can't kill me; you're not opped in %s"
                             % self.channel, target)

        # Other
        elif not self.quiet:
            raise CommanderError('unknown command (%s)' % cmd)

    def do_listen(self, cmd, target, nick):
        """
        Actually *do* the "listen" commands.

        We try to parse the command passed from do_command, and alter
        it as we successfully get each argument.

        """
        if cmd.startswith("list"):
            listenchannels = query(queries["listenchannels"])
            self.msg("'listen' channels: "+", ".join(listenchannels), target)
        elif cmd.startswith("add"):
            text = re.sub("^add", "", cmd).strip()
            channel = text.split(" ")[0]
            if not channel:
                if not self.quiet:
                    self.msg("You have to specify a channel", target)
            else:
                if not channel.startswith("#"):
                    channel = "#" + channel
                if len(query('select l_channel from listen where '
                             'l_channel="%s"' % channel)) > 0:
                    if not self.quiet:
                        self.msg("%s is already in the list of 'listen' "
                                 "channels!" % who, target)
                else:
                    modquery('insert into listen values (0, "%s")' % channel)
                    # Update the list of listen channels
                    self.listenchannels = query(queries["listenchannels"])
                    if not self.quiet:
                        self.msg("%s added to the list of 'listen' channels!"
                                 % channel, target)
                    self.connection.join(channel)
        elif self.startswitharray(cmd, ["remove", "delete"]):
            text = re.sub("^(remove|delete)", "", cmd).strip()
            channel = text.split(" ")[0]
            if not channel:
                if not self.quiet:
                    self.msg("You have to specify a channel", target)
            else:
                if not channel.startswith("#"):
                    channel = "#" + channel
                if len(query('select l_channel from listen where '
                             'l_channel="%s"' % channel)) == 0:
                    if not self.quiet:
                        self.msg("%s is not in the list of 'listen' channels!"
                                 % channel, target)
                else:
                    modquery('delete from listen where l_channel="%s"'
                             % channel)
                    # Update the list of listen channels
                    self.listenchannels = query(queries["listenchannels"])
                    if not self.quiet:
                        self.msg("%s removed from the list of 'listen' "
                                 "channels!" % channel, target)
                    self.connection.part(channel, "Requested by %s in %s"
                                         % (nick, self.channel))
        elif self.startswitharray(cmd, ["change", "edit",
                                        "modify", "rename"]):
            text = re.sub("^(change|edit|modify|rename)", "", cmd).strip()
            channels = text.split(" ")
            if len(channels) < 2:
                if not self.quiet:
                    self.msg("You have to specify two channels", target)
            else:
                chan1 = channels[0]
                chan2 = channels[1]
                if not chan1.startswith("#"):
                    chan1 = "#" + chan1
                if not chan2.startswith("#"):
                    chan2 = "#" + chan2
                if len(query('select l_channel from listen where '
                             'l_channel="%s"' % chan1))==0:
                    if not self.quiet:
                        self.msg("%s is not in the list of stalked pages!"
                                 % chan1, target)
                else:
                    modquery('update listen set l_channel = "%s" where '
                             'l_channel = "%s"' % (chan2, chan1))
                    # update the list of listen channels
                    self.stalked = query(queries["listenchannels"])
                    if not self.quiet:
                        self.msg("Changed the name of %s in the list of "
                                 "'listen' channels!" % chan1, target)
                    self.connection.part(chan1, "Requested by %s in %s"
                                         % (nick, target))
                    self.connection.join(chan2)
        elif cmd.startswith("on"):
            if not self.listen and self.listenchannels:
                for chan in self.listenchannels:
                    self.connection.join(chan)
                if not self.quiet:
                    self.msg("Joined the 'listen' channels.", target)
                self.listen = True
        elif cmd.startswith("off"):
            if self.listen and self.listenchannels:
                for chan in self.listenchannels:
                    self.connection.part(chan)
                if not self.quiet:
                    self.msg("Parted the 'listen' channels.", target)
                self.listen = False
        else:
            CommanderError('unparseable command (%s)' % cmd)

    def do_status(self, cmd, target):
        """
        Actually *do* the "status" commands.

        We try to parse the command passed from do_command, altering
        the string as we successfully get each argument.

        """
        if cmd.startswith("list"):
            text = re.sub("^list", "", cmd).strip()
            which = text.split(" ", 1)[0]
            if not which or which == 'all':
                # False lets us use more than one column
                statuses = query(queries["getstatuses"], False)
            elif which == 'ok':
                statuses = query(queries["getok"], False)
            elif which == 'down' or which == 'notok' or which == 'problems':
                statuses = query(queries["getproblems"], False)
            out0 = [] # s_ok=0 (False - down)
            out1 = [] # s_ok=1 (True - up)
            for row in statuses: # iterate over the rows
                #('service', 'um, something is wrong', 0)
                if row[2] == True:
                    out1.append("%s: \x0303%s\x0F" % (row[0], row[1]))
                else:
                    out0.append("\x0305%s:\x0F %s" % (row[0], row[1]))
            if len(out0) > 0:
                self.msg("\x02Current status:\x0F", target)
                # Output all problems on their own line,
                # then all OKs on one line
                for row in out0:
                    self.msg(row, target)
                self.msg(" ¦ ".join(out1), target)
            else:
                # Output everything on one line
                self.msg("\x02Current status:\x0F %s"
                         % " ¦ ".join(out1), target)
        elif cmd.startswith("set"):
            text = re.sub("^set", "", cmd).strip()
            service = text.split(" ", 1)[0]
            status = text.split(" ", 1)[1]
            if not service:
                if not self.quiet:
                    self.msg("You have to specify a service", target)
            elif service == 'all clear':
                self.do_status('ok all', target) # Don't duplicate code
            elif not status:
                if not self.quiet:
                    self.msg("You have to specify a status", target)
            else:
                if len(query('select s_service from status where '
                             's_service="%s"' % service)) == 0:
                    if not self.quiet:
                        self.msg("%s is not a listed service"
                                 % service, target)
                else:
                    modquery('update status set s_state="%s",s_ok=false '
                             'where s_service="%s"' % (status, service))
                    if not self.quiet:
                        self.msg("%s now has status '%s'"
                                 % (service, status), target)
        elif cmd.startswith("ok"):
            text = re.sub("^ok", "", cmd).strip()
            service = text.split(" ", 1)[0]
            if not service:
                if not self.quiet:
                    self.msg("You have to specify a service", target)
            else:
                if service == 'all':
                    modquery(queries['setallclear'])
                    if not self.quiet:
                        self.msg("\x0303All clear!\x0F", target)
                elif len(query('select s_service from status where '
                               's_service="%s"' % service)) == 0:
                    if not self.quiet:
                        self.msg("%s is not a known service"
                                 % service, target)
                else:
                    modquery('update status set s_ok=true,s_status="OK" '
                             'where s_service="%s"' % service)
                    if not self.quiet:
                        self.msg("Recorded %s as OK" % service, target)
        else:
            raise CommanderError('unparseable command (%s)' % cmd)

    def do_service(self, cmd, target):
        """
        Actually *do* the "service" commands.

        We try to parse the command sent from do_command, and
        execute it, altering the string as we get each argument.

        """
        if cmd.startswith("list"):
            self.do_status("list all", target) # Don't duplicate code
        elif cmd.startswith("set"):
            self.do_status("status %s" % cmd, target) # Don't duplicate code
        elif cmd.startswith("add"):
            text = re.sub("^add", "", cmd).strip()
            service = text.split(" ")[0]
            if not service:
                if not self.quiet:
                    self.msg("You have to specify a service", target)
            else:
                if len(query('select s_service from status where '
                             's_service="%s"' % service)) > 0:
                    if not self.quiet:
                        self.msg("%s is already in the list of services!"
                                 % service, target)
                else:
                    modquery('insert into status values (0, "%s", "OK", true)'
                             % service)
                    if not self.quiet:
                        self.msg("%s added to the list of services!"
                                 % service, target)
        elif self.startswitharray(cmd, ["remove", "delete"]):
            text = re.sub("^(remove|delete)", "", cmd).strip()
            service = text.split(" ")[0]
            if not service:
                if not self.quiet:
                    self.msg("You have to specify a service", target)
            else:
                if len(query('select s_service from status where '
                             's_service="%s"' % service)) == 0:
                    if not self.quiet:
                        self.msg("%s is not in the list of services!"
                                 % service, target)
                else:
                    modquery('delete from status where s_service="%s"'
                             % service)
                    if not self.quiet:
                        self.msg("%s removed from the list of services!"
                                 % service, target)
        elif self.startswitharray(cmd, ["change", "edit", "modify", "rename"]):
            text = re.sub("^(change|edit|modify|rename)", "", cmd).strip()
            services = text.split(" ")
            if len(services) < 2:
                if not self.quiet:
                    self.msg("You have to specify two names", target)
            elif len(services) == 2:
                s1 = services[0]
                s2 = services[1]
                if len(query('select s_service from status where '
                             's_service="%s"' % s1)) == 0:
                    if not self.quiet:
                        self.msg("%s is not in the list of services!"
                                 % s1, target)
                else:
                    modquery('update status set s_service="%s" where '
                             's_service="%s"' % (s2, s1))
                    if not self.quiet:
                        self.msg("Changed the name of service '%s' to '%s'"
                                 % (s1, s2), target)
            else:
                raise CommanderError('too many parameters (%s)' % cmd)
        else:
            raise CommanderError('unparseable command (%s)' % cmd)

    def msg(self, msg, target=None):
        """
        Send a message to either a channel or by PM to a user.

        Target determines whether the message is sent to a channel
        or a user (by PM). If not given, this defaults to self.channel.

        """
        if not target:
            target = self.channel
        self.connection.privmsg(target, msg)

    def startswitharray(self, a, l):
        """
        Determine if a string starts with any of the strings in a list.

        This is just a version of str.startswith() that takes a
        list of strings to check, instead of just one.

        """
        for i in l:
            if a.startswith(i):
                return True
        return False

    def randmess(self):
        """
        Determine pseudo-randomly whether to send a specified message.

        This might eventually send a message periodically. Or it
        might be culled, or rewritten, or abandoned at sea.

        """
        if self.dorandmess:
            a = int(random.random()*1000)
            b = int(random.random()*1000)
            if a == b:
                self.msg(randmessage)

class StatusbotException(Exception):
    """
    A single base class for all other statusbot exceptions.

    """
    pass

class CommanderError(StatusbotException):
    """
    Raise this exception when the command can't be parsed.

    """
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return "CommanderError (%s)" % repr(self.value)

def main():
    """
    Actually run stuff!

    """
    global bot
    bot = FreenodeBot()
    bot.start()

if __name__ == "__main__":
    """
    Actually run stuff!

    """
    global bot
    try:
        main()
    except IOError:
        print ("No config file. You should start this script from "
                         "its directory like 'python statusbot.py'")
    except:
        # Re-raise the last exception that brought us
        # here. Without it, this bare except would be evul.
        raise
        bot.die()
        sys.exit()


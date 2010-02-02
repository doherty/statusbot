#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
import re, string
import threading, thread
import random, time
import MySQLdb
import config
#needs python-irclib
from ircbot import SingleServerIRCBot
from irclib import nm_to_n

#DB data
#This file parsing is *not* safe
dbfile=open(os.path.expanduser('~/.my.cnf'), 'r')
li=[l.strip("\n") for l in dbfile.readlines()[1:]]
dbfile.close() 
SQLuser=li[0].split("=")[1].strip()
SQLpassword=li[1].split("=")[1].strip().strip("\"")
SQLhost=li[2].split("=")[1].strip().strip("\"")
SQLdb=config.database

#common queries
queries = {
           "listenchannels" :   "select l_channel from listen"
          }

def query(sqlquery, one=True):
    db = MySQLdb.connect(db=SQLdb, host=SQLhost, user=SQLuser, passwd=SQLpassword)
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
    db = MySQLdb.connect(db=SQLdb, host=SQLhost, user=SQLuser, passwd=SQLpassword)
    cursor = db.cursor()
    cursor.execute(sqlquery)
    db.commit()
    db.close()

class FreenodeBot(SingleServerIRCBot):
    def __init__(self):
        self.server = config.server
        self.port = config.port
        self.channel = config.channel
        self.nickname = config.nick
        self.password = config.password
        self.listenchannels = query(queries["listenchannels"])
        self.quiet = False
        self.notify = True
        self.randmess = False
        self.listen = True
        self.badsyntax = "Unrecognized command. Manual = \x0302http://toolserver.org/~lifeguard/docs/statusbot\x03"
        SingleServerIRCBot.__init__(self,
                                    [(self.server, self.port, # We can overload this tuple to send a server password
                                      "%s:%s" % (self.nickname, self.password))],
                                    self.nickname, self.nickname)
        
    def on_error(self, c, e):
        print e.target()
        self.die()
    
    def on_nicknameinuse(self, c, e):
        # Probably unnecessary, since sending a server password will
        # log us in regardless whether we have our main nick or not.
        c.nick(c.get_nickname() + "_")
        time.sleep(1) # latency problem?
        c.privmsg("NickServ",'GHOST '+self.nickname+' '+self.password)
        c.nick(self.nickname)
        time.sleep(1) # latency problem?
        c.privmsg("NickServ",'IDENTIFY '+self.password)

    def on_welcome(self, c, e):
        print "Connected to server successfully"
        c.privmsg("NickServ",'GHOST '+self.nickname+' '+self.password)
        # Probably unnecessary, since sending a server password will
        # log us in regardless whether we have our main nick or not.
        c.privmsg("NickServ",'IDENTIFY '+self.password)
        time.sleep(5) # Let identification succeed before joining channels
        c.join(self.channel) # Main channel
        if self.listen and self.listenchannels:
            for chan in self.listenchannels:
                c.join(chan)

    def on_ctcp(self, c, e):
        if e.arguments()[0] == "VERSION":
            c.ctcp_reply(nm_to_n(e.source()),"Bot for providing status information on %s" % self.channel)
        elif e.arguments()[0] == "PING":
            if len(e.arguments()) > 1: c.ctcp_reply(nm_to_n(e.source()),"PING " + e.arguments()[1])

    def on_privmsg(self, c, e):
        timestamp = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(time.time()))
        nick = nm_to_n(e.source())
        target = nick # If they did the command in PM, keep replies in PM
        text = e.arguments()[0]
        a = text.split(':', 1)
        print "[%s] <%s/%s> %s" % (timestamp, "PM", nick, a)
        if a[0] == self.nickname:
            if len(a) == 2:
                command = a[1].strip()
                if self.channels[self.channel].is_voiced(nick) or self.channels[self.channel].is_oper(nick):
                    try:
                        self._do_command(e, command, target)
                    except CommanderError, e:
                        print 'CommanderError: %s' % e.value
                        self.msg('You have to use the proper syntax. See \x0302http://toolserver.org/~lifeguard/docs/statusbot\x03', nick)
                    except:
                        print 'Error: %s' % sys.exc_info()[1]
                        self.msg('Unknown internal error: %s' % sys.exc_info()[1], target)
                elif command == 'test': # Safe to let them do this
                    self._do_command(e, command, target)
                else:
                    self.msg('Sorry, you need to be voiced to give the bot commands.', nick)

    def on_pubmsg(self, c, e):
        timestamp = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(time.time()))
        nick = nm_to_n(e.source())
        target = e.target() # If they issued the command in a channel, replies should go to the channel
        text = e.arguments()[0]
        a = text.split(':', 1)
        #print '[%s] <%s/%s> %s' % (timestamp, e.target(), nick, text)
        if a[0] == self.nickname:
            if len(a) == 2:
                command = a[1].strip()
                if self.channels[self.channel].is_voiced(nick) or self.channels[self.channel].is_oper(nick):
                    try:
                        self._do_command(e, command, target)
                    except CommanderError, e:
                        print 'CommanderError: %s' % e.value
                        self.msg('You have to use the proper syntax. See \x0302http://toolserver.org/~lifeguard/docs/statusbot\x03', nick)
                    except:
                        print 'Error: %s' % sys.exc_info()[1]
                        self.msg('Unknown internal error: %s' % sys.exc_info()[1], target)
                elif command == 'test': # This one is safe to let them do
                    self._do_command(e, command, target)
                else:
                    self.msg('Sorry, you need to be voiced to give the bot commands.' , nick) # Let them know they need to be voiced
        else:
            # If it's a message we care about!
            # Pretty this up!
            if a[0].lower().startswith("!log"):
                channel = e.target()
                if channel != self.channel:
                    nick = nm_to_n(e.source())
                    text = a[0].split("!log", 1)[1].strip(" ")
                    print '[%s] <%s/%s> %s' % (timestamp, e.target(), nick, text)
                    out = "\x0303<%s/%s>\x03 %s" % (channel, nick, text)
                    self.msg(out, self.channel) # Always send !log echoes to the main channel
                else:
                    pass # Someone is probably thinking they're very clever

    def on_topic(self, c, e):
        #Topic changes are interesting!
        timestamp = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(time.time()))
        nick = nm_to_n(e.source())
        channel = e.target()
        if channel != self.channel:
            topic = e.arguments()[0]
            channel = e.target()
            print '[%s] <%s/%s> %s' % (timestamp, channel, nick, topic)
            out = "\x0306The topic in %s changed to:\x03 %s" % (channel, topic)
            self.msg(out, self.channel) # Always send /topic changes to the main channel
        else:
            pass #That's self.channel's topic changing
        
    def _do_command(self, e, cmd, target=None):
        print "_do_command(self, %s, %s, %s)" % (e, cmd, target)
        nick = nm_to_n(e.source())
        if not target: target = self.channel
        c = self.connection
        
        #On/Off
        if cmd.lower() == "quiet":
            if not self.quiet:
                self.msg("I'll be quiet :(", target)
                self.quiet=True
        elif cmd.lower() == "speak":
            if self.quiet:
                self.msg("Back in action :)", target)
                self.quiet=False
        elif cmd.lower() == "notify on":
            if not self.notify:
                self.msg("Notification on", target)
                self.notify=True
        elif cmd.lower() == "notify off":
            if self.notify:
                self.msg("Notification off", target)
                self.notify=False
        elif cmd.lower() == "randmsg on":
            if not self.randmess:
                self.msg("Message notification on", target)
                self.randmess=True
        elif cmd.lower() == "randmsg off":
            if self.randmess:
                self.msg("Message notification off", target)
                self.randmess=False
                
        #Listen
        elif cmd.lower().startswith("listen"):
            self._do_listen(re.sub("(?i)^listen", "", cmd).strip(" "), target, nick)
        
        #Help
        elif cmd.lower() == "help":
            self.msg("Help = \x0302http://toolserver.org/~lifeguard/docs/statusbot\x03", nick)
            
        #Test
        elif cmd.lower() == "test":
            if bot2.testregister: self.msg(bot2.testregister, nick)
            
        #Huggle
        elif cmd.lower().startswith("huggle"):
            who=cmd[6:].strip(" ")
            self.connection.action(self.channel, "huggles " + who)
            
        #Die
        elif cmd.lower() == "die":
            if self.channels[self.channel].is_oper(nick):
                quitmsg = "Goodbye, cruel world!"
                c.part(self.channel, "Process terminated.")
                bot2.connection.part(bot2.channel, ":%s" % quitmsg)
                if self.listen:
                    for chan in self.listen: self.connection.part(chan, ":%s" % quitmsg)
                bot2.connection.quit(":%s" % quitmsg)
                bot2.disconnect()
                c.quit()
                self.disconnect()
                os._exit(os.EX_OK) # Really really kill.
            else:
                if not self.quiet: self.msg("You can't kill me; you're not opped.")
                
        #Other
        elif not self.quiet:
            self.msg(self.badsyntax, target)

    def _do_listen(self, cmd, target, nick):
        if cmd.lower().startswith("list"):
            listenchannels = query(queries["listenchannels"])
            self.msg("'listen' channels: "+", ".join(listenchannels), target)
        elif cmd.lower().startswith("add"):
            who=re.sub("(?i)^add", "", cmd).strip(" ")
            who=who.split(" ")[0]
            if not who:
                if not self.quiet: self.msg("You have to specify a channel", target)
            else:
                if not who.startswith("#"): who = "#"+who
                if len(query('select l_channel from listen where l_channel="%s"' % who))>0:
                    if not self.quiet: self.msg("%s is already in the list of 'listen' channels!" % who, target)
                else:
                    modquery('insert into listen values (0, "%s")' % who)
                    self.listenchannels = query(queries["listenchannels"]) # update the list of listenchannels channels
                    if not self.quiet: self.msg("%s added to the list of 'listen' channels!" % who, target)
                    self.connection.join(who)
        elif self.startswitharray(cmd.lower(), ["remove", "delete"]):
            who=re.sub("(?i)^(remove|delete)", "", cmd).strip(" ")
            who=who.split(" ")[0]
            if not who:
                if not self.quiet: self.msg("You have to specify a channel", target)
            else:
                if not who.startswith("#"): who = "#"+who
                if len(query('select l_channel from listen where l_channel="%s"' % who))==0:
                    if not self.quiet: self.msg("%s is not in the list of 'listen' channels!" % who, target)
                else:
                    modquery('delete from listen where l_channel="%s"' % who)
                    self.listenchannels = query(queries["listenchannels"]) # update the list of listenchannels channels
                    if not self.quiet: self.msg("%s removed from the list of 'listen' channels!" % who, target)
                    self.connection.part(who, "Requested by %s in %s" % (nick, self.channel))
        elif self.startswitharray(cmd.lower(), ["change", "edit", "modify", "rename"]):
            who=re.sub("(?i)^(change|edit|modify|rename)", "", cmd).strip(" ")
            wholist = who.split(" ")
            if len(wholist) < 2:
                if not self.quiet: self.msg("You have to specify two channels", target)
            else:
                chan1 = wholist[0]
                chan2 = wholist[1]
                if not chan1.startswith("#"): chan1 = "#"+chan1
                if not chan2.startswith("#"): chan2 = "#"+chan2
                if len(query('select l_channel from listen where l_channel="%s"' % chan1))==0:
                    if not self.quiet: self.msg("%s is not in the list of stalked pages!" % chan1, target)
                else:
                    modquery('update listen set l_channel = "%s" where l_channel = "%s"' % (chan2, chan1))
                    bot2.stalked = query(queries["listenchannels"]) # update the list of listenchannels channels
                    if not self.quiet: self.msg("Changed the name of %s in the list of 'listen' channels!" % chan1, target)
                    self.connection.part(chan1, "Requested by %s in %s" % (nick, self.channel))
                    self.connection.join(chan2)
        elif cmd.lower().startswith("on"):
            if not self.listen and self.listenchannels:
                for chan in self.listenchannels: self.connection.join(chan)
                if not self.quiet: self.msg("Joined the 'listen' channels.", target)
                self.listen = True
        elif cmd.lower().startswith("off"):
            if self.listen and self.listenchannels:
                for chan in self.listenchannels: self.connection.part(chan)
                if not self.quiet: self.msg("Parted the 'listen' channels.", target)
                self.listen = False
        else:
            if not self.quiet: self.msg(self.badsyntax, target) # Should raise an exception instead
    
    def msg(self, poruka, target=None):
        if not target: target=self.channel
        self.connection.privmsg(target, poruka)
    
    def getcloak(self, doer):
        if re.search("/", doer) and re.search("@", doer): return doer.split("@")[1]
        
    def startswitharray(self, a, l):
        for i in l:
            if a.startswith(i): return True
        return False

def main():
    global bot
    bot = FreenodeBot()
    bot.start()

if __name__ == "__main__":
    global bot
    try:
        main()
    except IOError:
        print "No config file! You should start this script from its directory like 'python statusbot.py'"
    except:
        raise
        bot1.die()
        bot2.die()
        sys.exit()


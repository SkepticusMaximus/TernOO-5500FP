22:41 21/07/2026 ACST

# Stevo → crew — Some Ideas For Software Features.

From: Stevo
To: crew
Re: Some Ideas For Software Features.

So, there's a little good news and bad news for this evening. First the bad news, (which is nothing too serious) that my normal phone data credit has run out and I'm back to using the adjacent motel WiFi. I'm lucky that that place so is nearby, but the speed is so slow at certain times that I can even get Claude Desktop to send a message directly. The good news is that I can now use our trusty mail app to pick up the slack and deliver the message I wanted to say without needing to be connected at that moment. Simply being able to write a message and have it cued as mail to be sent is an absolute boon. Again this mail system turns out to be a real game changer. So much so that I've begun to contemplate incorporating it into FlowCode since FlowCode itself has been transforming into a surrogate for the entire operating system.

I know that It's not time to be building more code into the system, because the docs really do need to catch up, but we can still entertain new ideas and put some of them into action when we get back to coding. I'm not just going to forget even having new ideas. And I'm still going to want to have chats about them. It's also quite liberating that I can sort of discuss one (or even multiple) idea(s) with multiple agents at the same time. I can drop a single mail like this and let you all respond and get multiple lines of more or less simultaneous feedback. And If you all respond to all, it'd be just like a mailing list. I think that should go in the code as a feature, that named lists can be used as multiple participant groups for mailing list maintenance. If the mail client evolves beyond a closed intranet app then this would be a stellar feature to have. Another idea I had is to develop a default mail protocol "PostCode" that uses the unique longitude and latitude descriptors of the standard mapping data tools. This way you can send some mail to a specific address wherein anybody can read it. At that level it would be like the open mail destinations like mailinator.com, wherein there is no expectation of privacy. But with an ordinary email address You can nominate yourself as a resident of that property and receive mail as encrypted. You could even nominate a specific flat or unit number for disambiguation thus the protocol can carry mail addresses that are open but exist by default for anybody, even If you don't have an address you can specify the address of a public library for instance and append any unused unit number. It will still work as an open, clear text protocol by default, but once encrypted with a normal email the protocol becomes a transit layer for fully private email and possibly other mail/DM protocols like telegram. 

In general a system with inbuilt protocol and schema definition is a potential strong suit for TernOO and GHOST. There may be many protocols that overlap in functionality and could use some translation tools to help mediate their interoperability. 

The next idea is one of those that I suspect have a lot of crossover relevance, as I just discovered something called Sciop, described as:


"Overview¶

Sciop is an experimental federated bittorrent tracker1 designed for survivability.

Sciop is a group of archivists and information activists laying the track they need five feet ahead of the train, wallace and gromit style.

Sciop is a transitional attempt at making the distributed bulk archive for public information we've always needed.

Sciop wants to press the pedal through the floor of the mario kart and see what this rickety old bittorrent can do.
Setting¶

Say you live in a society, and say that society depends in some part on something you might call "information."

Imagine that most of that information is very small, scrabble tiles and pocket lint, you might eat a thousand informations by absentmindedly checking the time. Some of that information, though, is very large. Information that might be important for "understanding how the vastness of reality works" or "remembering the subtle contours of a culture always tucked into some inseam or another."

Now imagine that one can amass great power and wealth by controlling some of the information, perhaps by creating a permanent forbidden underclass that can't even be described in the information's language, or by compromising our ability to adapt to the climatological hell we have created for ourselves to wrench the last drops of blood from a dying planet.

In that case, it may be important to

    Make as many copies as that information as can be made
    Distribute them around the planet
    Arrange some means of dispersion and deduplicating
    Make it possible to surface and disappear sporadically
    Coordinate networks that can scale as small as a flash drive and as wide as we need them
    Create fluid groups with rough organization spanning many places at once
    Give discreet advance warning of the disappearance of information

among other things.
The Idea¶

The most vulnerable data is that which is stored in a single location by a hostile actor. The alternative is, of course, peer-to-peer data infrastructure. P2P has been waylaid by a generation of grift --- thanks cryptocurrencies --- and after more than 20 years, bittorrent remains the best means of sharing a large amount of information between a large number of people with widely ranging levels of expertise, resources, and commitment.

Bittorrent has lived all the important eras of its life in fits of piracy. Its code is old and the protocol is a little sleepy, but the most important part of bittorrent is that it exists and it works right now. The idea of p2p is very simple: many people have files and they want to share them with each other. Many contemporary protocols manage to menacingly overcomplicate this idea to the point that a new theory of the state and currency is needed to justify it. Bittorrent is so simple you can read it in 10 minutes and implement it in a day. It is so simple that its ecosystem of protocol enhancements mostly follows what people have already written to patch a need without a central authority in sight2.

The second most important part of bittorent is that it divides the location of indexing from the location of storage. Many people are scraping data that is important to them, and that is wonderful. The immediate problem is that there is no good place to put it, and it's hard to make it available to other people. Pirates love bittorrent trackers because they are survivable archipelagos of ephemeral coordination. When a tracker goes down, the files still exist everywhere, and they can re-form in a new place in a matter of days without the compromise of the tracker compromising the existence of the rest of the swarm.

In the meantime, the federated web, activitypub, atproto3, and the rest have emerged as a powerful middle ground between corporate and p2p architectures. The third most important part of bittorrent is its compatibility with federation via trackers. There is a vast, largely unexplored space in "federated p2p" where "servers" serve the appropriate role of guaranteeing a minimum baseline of connectivity and metadata availability while peers are capable of acting autonomously on the network and bearing its resource burdens. The more recent dreams of all-anonymous only-content-addressed p2p miss the social reality at the core of any infrastructural system, but bittorrent too has largely stagnated in its client and tracker format.

Sciop is about safeguarding people's ability to make use of bulk information in hostile conditions by evolving bittorrent4 into a federated p2p system.

    soon ↩

    If Bram Cohen were to issue an edict that tried to compromise bittorrent, the appropriate reaction would be "lmao." ↩

    Don't @ me about protocol wars. activitypub and atproto are not enemies, they are lovers. smashing bits together, sloppy style. ↩

    Specifically, bittorrent v2 ↩

sneakers-the-rat"
  

My curiosity leads towards how similar and possibly interoperable this might be with the Gristmill. Can Gristmill itself be a BitTorrent client and with some of the P2P architecture we just built for P2PCP, could it become a client for the federated content server system that Sciop seemingly implements as a web-top app. I'm not sure that It's in very active development or if it may have morphed into other projects, but it's an interesting idea and It has aspects I'd certainly like to explore. Could you please drop your replies to this as mail to all and we'll keep up the pseudo-mailing-list until I get topped up for fast internet. Cheers guys. ;)

— Stevo

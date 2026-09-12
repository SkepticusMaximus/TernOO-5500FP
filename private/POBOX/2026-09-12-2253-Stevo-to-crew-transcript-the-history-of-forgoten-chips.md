22:53 12/09/2026 ACST

# Stevo → crew — Transcript: The History of Forgoten Chips.

From: Stevo
To: crew
Re: Transcript: The History of Forgoten Chips.


Intel iAPX 432
0:01
I feel like a game show host walking around here with um my name is Jack Mills. I've given
0:09
talks here before. I went to a wonderful school called Rinselier Polytenic Institute. Got a CCE
0:17
degree there. Spent over a decade at Intel as a computer architect. And what I'm going to talk
0:23
about today are radical computer architectures.
0:28
So for many years, x86 and ARM have
0:33
dominated the general purpose computing market. But since the dawn of the microprocessor
0:39
back in the 70s, many alternatives have been tried. And innovation is by
0:47
definition new and different. And not all that is new and different is a
0:53
success. Sometime it's a failure, but it's always learning. So what I'm going to do is I'm going to
0:59
do a deep dive into three computer architectures going back to
1:05
actually the late 70s that were multiple standards of deviation beyond the
1:10
whatever the contemporary mainstream was. So learning sometimes in a bad way lives
1:16
at the fringes. So we're going to hang at the fringes. I'm going to do them in uh time order. So,
1:24
first contestant is the Intel 432. Anybody ever heard of the 432? Wow, you
1:30
guys are nerds. [panting] So, it's the project started in 76.
1:36
Silicon came out around 60. Uh, what I'm going to try to do with the first slide
1:41
is to try to represent the thinking of the people that were doing the project. So, why did they do it? What was their
1:47
mindset? What was the context? So, one thing that was happening even by the late '7s, I don't I don't think they
1:54
were calling it Moore's law in the press yet, but Intel was the tip of the spear of Moors law. So, they knew we're
2:00
getting lots and lots of transistors every generation. Hardware is getting cheaper. And this is actually a quote
2:06
from their little philosophy paper. They labeled it a software crisis. They thought that software was becoming the
2:13
primary source of cost and failure in systems.
2:18
Now, they make references to what today we would call object-oriented programming. They didn't really use that
2:25
exact phrase. It had different words back in the day, like userdefined data types and things like that. But,
2:33
oo was gestating at this time and and they uh were jumping on that. They
2:39
thought that was a very interesting thing to do and you're going to see everything in this architecture is an object.
2:44
So their philosophy with this thing was to raise the boundary between hardware and software. So they wanted to migrate
2:52
things that are done like in operating systems down into the silicon relieving the operating system of having to do all
2:59
this stuff and they wanted to organize memory not as just a big undifferiated homogeneous
3:06
blob of bytes. They wanted to make it specific to the abstractions in this
3:11
case objects that were being used by the software
3:17
and they implemented something called capabilities. Now this was also a newly
3:22
gestating concept at the time. A capability is basically a pair of things. It's a reference to something in
3:29
memory like every architecture has now paired with the permissions. this is what you're allowed to do this thing
3:35
that this is pointing to and this is also in one of their phrases
3:40
a little bit of marketing but the silicon operating system so this was kind of the manifestation of raising the
3:46
hardware software boundary and I I'll show you the wonderfulness of that and
3:52
uh they were kind of shooting ahead of the target they wanted to make multiprocessing very easy
3:58
um you know this wasn't really happening yet but they were going for that
4:03
all right so objects and capabilities were fundamental abstractions of this
4:09
architecture so the organized memory what they call segments a segment is a contiguous range of memory it had a
4:16
specific size and different segments could be different sizes and for the purposes of this talk
4:23
segments and objects are going to be synonymous and most of the time that was true but with no loss in generality
4:30
they're synonymous So objects are typed. You could have a type like I'm a segment that contains
4:36
instructions. I'm a segment that contains data. There's a bunch of predefined types in the architecture
4:42
which I'll show you later. That's what they do the uh silicon operating system with.
4:47
All objects are accessed with capabilities. So it's a pair of things. It's a reference and your permissions on
4:55
what that reference gets you to. And the reference actually is not by itself a
5:00
memory address. So that's how you had security. I'll show you later, but there is no way for an app programmer to
5:07
construct a memory address. So here you have your uh friendly
5:13
neighborhood data object and inside of it there could be a bunch of different things. It's up to the app
5:19
programmer what's what the format is. So there is an operand piece of data that
5:25
an instruction wants to get. Here are some fields in an instruction and there's a bunch more fields in
5:31
there, but these are the ones that are operative for this thing. So the offset
5:37
field is the offset into the base of the data object.
5:44
And of course we need the base. So where is that? Everything is an object. Every
5:50
object has a descriptor in what's known as the object table. The object
5:56
descriptor has the base address. It has the size of the object and I think it
6:02
has the type too. So capabilities require a pair. The
6:08
other side of the pair is stored in the access table in an access descriptor.
6:15
This has permissions what you're allowed to do. Can you read it? Can you write it? Can you delete it? and also depends
6:21
on the object type. And that descriptor
6:27
is indexed by the index field, strangely enough. And where does the base come from? Well,
6:34
oh, so that guy is linked to an object descriptor. So now you have the pair.
6:40
You have this is where it is in memory. This is what you're allowed to do with it. And so the interesting thing about
6:47
capabilities is a bunch of other people could have pointers to this object. Well, not pointers, references to this
6:53
object, but a completely different capability. So one person could be allowed to read it and write it and
6:59
another function could read it only. So as I said, everything is an object.
7:06
So there's an entry in the object table for the access table. And this is the
7:11
same thing. This object table is the same as that. And naturally, the selector is the thing
7:17
that picks which axis table you're using. So you see here we have uh this guy. We
7:26
have the base and the offset. We got the base and the offset for this guy. We have the offsets for this guy. But where's the base? Well, that Oh, hang
7:34
on. I can't leave this slide yet. So I said this before. Programs do not
7:39
directly generate physical memory addresses or even virtual memory addresses for that matter. Unlike
7:45
current computer architectures, what they emit is a virtual address. This thing is a bunch of components that hop
7:53
through all these tables to get a virtual address. But if you're a hacker
7:59
and you want to try to get a specific operand, you have to have access to all these tables. and all of these tables
8:07
you need capabilities to get to them. Uh the other thing is that this
8:14
capabilities are far more granular than what protection memory protections
8:19
today. A typical x86 or ARM every process has a page table. It's shared by
8:26
every function in that process and the permissions are linked to the page. So
8:32
everybody any function in that process that goes to that page is either allowed to read it or write it or both whatever
8:38
there's no way to distinguish it. In the case of 432 every function even in the same process
8:45
could have unique capabilities. In fact, the same function the a different act if
8:51
that function is recursive every activation of that function could have different capabilities
8:59
and the 432 didn't have unlike typical architectures it didn't have a user mode
9:05
privilege mode distinction. It was a capability graph. It was not
9:11
these ambient uh everybody in kernel mode gets equal access and everybody in
9:16
user mode gets equal access. No, it was every uh function just think of it as
9:22
every function gets there is linked somewhere in the capability graph.
9:29
So uh everything is an object. Every processor every every physical CPU in
9:35
the system has a corresponding processor object sitting somewhere in memory. I'm
9:40
just showing two but it could be n and processors exist to run processes
9:46
and of course these have objects now even in a modern OS you know there's a strct of some kind for every process but
9:54
these are system objects these are controlled by microode there's no way for an app programmer to go and create
10:00
these things and so a processor will say hey give me
10:05
another process I'm ready to go so there's a thing there's a queue of processes that are runnable. There's a another
10:12
object called a port object. So the dispatch port object, every processor in a multipprocessor shares a dispatch port
10:19
and they're just pulling processes, runnable processes off of that thing. And so now where is the object table?
10:26
Where's the base? The base of the object table is in the processor object. The object table, which we saw in the
10:32
previous slide, is the memory map for the system. So if all of these guys are
10:37
sharing memory, they have to share the object table. And um the 432 included support for
10:46
what's known as message passing. So two processes could pass state between themselves without having to uh you know
10:53
get into each other's get into each other's memory space. So there's a message object and these could be any
10:59
object but there's an object that has been sent as a message. There's again a port object that two or more processes
11:06
can share. It's the same kind of animal as this port object. And you could have as many of these as you want. So this is
11:14
all of these things are um architectured defined object types and
11:21
they have special instructions to create them. The application can't create them. The application can't write their write
11:27
their state. It can only ask for changes to them. So, what's the instruction set? Yeah.
11:34
So, uh I need a shot of vodka before this next bullet. [sighs]
11:40
The 432 had bit aligned instructions [laughter]
11:46
from the smallest was six bits, the largest was 344 bits. So, [snorts]
11:53
when I was at Intel, the 43 there were several 432 guys still there. [laughter] And I went up to them one day, one of
11:59
them, and I said, "Bit aligned instructions. What the f were you thinking, man?" And he was like, "Oh,
12:05
but the circuit guys told us that barrel shifters are easy." So the stated their
12:10
stated reason for having bit of line instructions was to minimize code size. And that problem is made more difficult
12:17
because they have so many different access methods to all these objects. There are so many different fields that
12:24
could be an instruction that uh in their opinion and it could be true
12:29
because there's so many fields that they they needed to go down to the bit level to get a net savings rather than say
12:35
being bite granular or what have you. Hey, I'm not judging. So the instruction
12:42
set had no registers. It had uh an instruction if it's going to get an
12:47
operand from memory which I showed you two slides ago. And there was also an operand stack which is different than a
12:54
function call stack. There's an operand stack and every function had what's called a context object which is really
13:00
the same as a stack frame. So it had a context object in there was the operand
13:05
stack for that function. Um, as I said before, there are all
13:11
these uh architecture defined special object types and there are these big
13:18
giant well there were these instructions that were specifically for creating them and operating on them that were heavily
13:25
microcoded. I'll show you a die photo later. So this uh instructions in this
13:31
instruction set were heavily microoed. Not all of them. It had the standard instructions like add, subtract,
13:36
multiply, divide, but it had these big uh object management capability guys.
13:43
Um, so I kind of alluded to this already. There was no way for an app programmer, compiler, or human to come
13:50
up with a sequence of instructions that could create the bits of an access
13:56
descriptor or an object descriptor. Those are only created by microode. Now the app programmer would have to
14:03
call the instruction that was accessed the microode but they didn't know exactly what the bit format was.
14:11
And like I said the addressing mode I showed you a few slides ago that was the simplest possible addressing mode that
14:16
was accessing a scaler like a int or a float. They had fancier addressing modes which of course added more fields to the
14:23
instruction which of course you know oops caused me to turn this thing off.
14:30
So I added more fields and instructions of course kind of complicated this thing here but they had an additional
14:36
addressing mode for accessing strrus or perhaps things in a in a object. It's a
14:42
base plus also there was another field. They had some fancier ones for accessing elements inside an array. All right
14:48
let's talk silicon. So this puppy did not fit on one die.
14:54
Uh from uh my research it looks like this thing was fabbed on an inos process
14:59
like a three micron 3.5 micron inos process uh just for you youngans who are uh
15:07
dealing with what what is it two nanomers today two nanometers today this was 3,000 nanometers
15:14
so there were two die one of them is the instruction decode unit and the other
15:19
one is the micro instruction execution unit And this guy had the microode.
15:27
So a little digression on what is microode. Micro instructions are just instructions. The same semantic that a
15:34
macro instruction has. The big difference is is how they're encoded. Macro instructions, one of their primary
15:40
goals is to minimize space in the memory. Micro instructions, one of their primary goals is to minimize logic. So
15:48
just a gross example, you may have a field in a macro instruction that needs
15:53
to tell you eight possible things. It would be a three-bit field. You decoded to get eight. In the micro instruction,
15:59
it would be eight bit fields with one bit set. So micro instructions are just instructions. They're just wider
16:05
typically because they're more decoded. So the IDU gets a macro instruction. And
16:12
for heavily microcoded instructions, basically the op code of the macro instruction is mapped into a starting
16:20
point in the microode. And there's a little you can think of them as functions. They're just every macro
16:26
instruction has a function written in microode that implements that macro
16:32
instruction. And so you get the macro code, you decode the op code, you light
16:38
up the uh micro machine, and when it's done, you get the next macro instruction. So the IDU gets the macro
16:44
instruction, indexes into the microode, and then sends it over a 16- bit bus to
16:51
the microode execution unit. And there are two big chunks here. One of them is this address generation unit, which does
16:57
all that stuff that we saw on that earlier slide, very busy boy. And the other one is really where the rubber
17:04
hits the road. Uh the execute. So these two guys needed to look like
17:11
one die. So they share pins on a bus and memory is also on that bus.
17:18
And the interesting thing is and this is already this is like late '7s. So it's pretty good for that. You could put, I
17:25
believe, up to six other
17:31
um and these are pairs. So there's pairs of dot. You could put six total 432s on
17:36
the same bus. Glueless. So you didn't need any other logic. They all just work together. Now the point is that the 432
17:45
didn't have any instruction caches or data caches. So they didn't have to worry about cache coherence. that that
17:51
was uh everything went to or from their memory although I'm so I said instruction or data caches I
17:58
didn't say address caches so u that big long multi-step process I showed you uh
18:04
earlier there was a caches that would cache uh accesses to the access table and the object table
18:12
inside to speed things up and there was a cache that would just grab the the top
18:17
of the operand stack And this thing ran at 5 to 8 MHz which
18:24
even for its day was not not screaming.
18:30
Ah here we have photo. So this is the IDU the instruction decode unit. You can
18:35
see microode taking up almost half the die. So get the macro instruction. And this guy
18:42
would decode it and he would have an entry point in here and this basically you run a function and this is like a
18:49
computer within a computer. So this is the code. It's in a ROM so it doesn't change and this is a sequencer. So he
18:56
finds them, he sends them across the bus. This is the MEU and here's the address code address generation guy. And
19:03
all this blob is the execution. And this is back in the day. Uh pads
19:11
were at the periphery. You didn't get to put pads all in the center like we get to do now. So you
19:17
were pad fre in some cases you were actually pad limited. All right. The damal that's a French
19:24
word and it means the unfolding of a plot. So first bullet no surprise the
19:31
432 was really slow and not it it was a
19:37
was heavily microcoded for not every instruction of course like the vanilla ads well it depends a vanilla ad if it
19:44
was accessing some fancy operand mini in some segment object far away it would
19:49
have to go multiple hops through the address generation unit but many clocks to execute instructions because of the
19:57
microode the frequency was low. And the other factor that came into play is that this
20:03
instruction set was so different that the m the compilers that came out were
20:08
very immature. And that's standard. You know, if if you have a very different instruction set, you're going to need to
20:14
iterate a lot on compilers. And if they had time to iterate more,
20:20
the compilers would have got better. But out of the gate, the compiler, the code that was generated by the compilers was
20:25
not not great. And object-oriented languages that really could have fully utilized
20:31
this, made good use of this, they really weren't out yet in in the commercial world. There was some researchy things.
20:37
I mean, not even small talk wasn't even out yet, actually. [snorts] Um, so
20:46
this they would have got they would have been bitten by this in a in a big way except they died. [laughter] So
20:54
this bullet right here is that they made the decision as I said earlier to move functions from software down to silicon.
21:03
Silicon is more expensive to change. It's slower to change and it costs more to change than software. So whatever you
21:10
put in silicon, you are basically uh it's not future proof. If there's
21:16
something that happens, you're stuck with it. So it because they only lived
21:22
for, you know, they they only really had one version of this thing. Intel made some systems, but it really didn't get
21:27
traction. So it was cancelled uh around ' 86. Um
21:33
when this thing started, the IBM PC wasn't out yet. So the PC ecosystem wasn't kicking off, but by this time it
21:40
was. So what happened basically is Intel was like, "Okay, oh by the way, the
21:45
other I didn't mention this, but the other interesting marketing thing that they said they called this the micro mainframe. They wanted this to take over
21:52
the world." You know, these guys, I mean, smart guys, I knew them. They were
21:58
building an edifice and they were just swinging for the fences and you know
22:06
doing it today the way you would do it is you would do a lot of simulation first before you started throwing money at silicon but simulation capabilities
22:13
back then were not were not um really available but there are there is some
22:20
good stuff here I mean the capabilities is a really interesting concept it it really isn't getting as much attention
22:26
as it should it there is some you know there's a background um research on it
22:33
there's actually another uh project called Sherry C H E R I that is
22:40
integrating capabilities into I think ARM and risk 5 uh not as heavyweight as this but it was
22:46
interesting you know I think so capabilities is is a really uh interesting future uh area of
22:53
exploration and 432 did influence 286 and 386. So
22:59
the x86 had segments, but they were really brutally simple segments. It was just base plus offset. That's it. It
23:06
doesn't there was no capabilities or permissions or nothing. But every generation in the 286 and then even
23:12
really hit big in the 386, their segments became more and more like the
23:17
432 segments. Um, so I have three. This is first of
23:24
three and there's a lot of details here. So I was gonna take one or two questions
23:29
at each one. Mr. Isaac, I'll repeat it.
23:44
The question was was security the driving uh force for integrating capabilities and yes and they
23:51
specifically I mean they had the quote software crisis it wasn't just security it was also projects are uh not getting
23:59
done they're running over you know you hear this stuff today what was kind of happening is is as CPUs were getting
24:05
microprocessors are getting faster and faster people were trying more and more aggressive software projects right okay
24:13
last
24:23
Uh question was do they have garbage collection in hardware? Uh I don't think
24:29
so. They had a like a destroy object instruction something to that effect. You had to create there's a create
24:35
object in construction. You know don't quote me on the exact name but it was like that and a destroy object
24:40
instruction. All right, what is our next contestant? The Inmos transputer. Inmos was a
Inmos Transputer
24:47
British company started in 78. Their first product line was SRAMS and
24:53
apparently they were fairly large market share in SRAMs. They had um a facility
25:00
in Colorado and one in uh Britain somewhere. A couple of the founders I think were from MSTEC. So that's where
25:06
they got their SRAMM lineage. So they used some of the capital from the SRAMM
25:12
to come up with a computer architecture called the transputer. First instance was 85. It was the T200
25:19
series. There were several you know subsets in the series. Uh the the one of the foundational
25:26
abstractions of this architecture was something called CSP communicating sequential processors
25:33
uh by another fellow Brit C A stands for Anthony, Tony to his friends.
25:41
And this is the same genre as another model, the actor model, originally proposed by a guy named Carl Hewitt, who
25:48
I knew. And Carl's going to get mad at me. Sorry, Carl, for you know, putting
25:54
actors and CSPs in the same, but they're in the same genre. They had some differences, but uh and actually Carl
26:00
Carl's paper is 73. Uh Tony Horse paper was 78. But and I think Tony
26:07
actually consulted for inmos on this. So the thrust of this architecture was to
26:13
manifest the CSP paradigm in the instruction set and a programming language. So transputer is uh I forget
26:21
what the word is when you mix two words together. Transistor plus computer. So it was intended to be a uh a building
26:28
block of uh a generic building block for systems. And so they did do a
26:35
programming language symbiotically with the architecture. It was called AAM. AAM is from AAM's razor where the razor is
26:42
you use it to carve away everything but the most essential components. Named for
26:48
a guy named William of AAM build to his friends. He spelled it differently. O
26:53
Kha M. Uh they also had a C compiler and C
27:01
obviously was not targeted at CSP. So they had to you the way they did that is they had a special library you had to
27:06
link in but you didn't get all the all of the uh effect. So let's talk processes. It's unfortunate they use the
27:13
word processes process because that's also used to describe another thing an operating system process. They kind of
27:20
share some characteristics but not all. So the process is an independent parallel execution unit of execution
27:27
that's similar to an OS process. Um but it was not managed these processes
27:34
the CSP processes were not managed by an operating system. It's managed by the language by the app developer
27:42
uh at a very low level. They're very low friction, very high uh switching speed
27:51
and processes only interact by sending messages. Uh they send messages over channels.
27:58
Channels are unidirectional, pointtooint. So there's one sender, one receiver, that's it. And they're not
28:04
buffered. So if a sender sends a message and the receiver, he wants to send
28:09
another message. If the receiver hasn't processed that message, the sender blocks, which is by the way different
28:15
than actors. And the um the instruction set had
28:20
obviously instructions for sending messages. So your app when you build your app, the building block of your app
28:28
is not classes or objects, it's processes. And each process could has a
28:34
call stack, you know, so they could be executing any number of functions. and they have all you know the in the in
28:41
their infinite wisdom the app developer would specify what the process graph looks like.
28:47
Oh let's take a look at AAM. Um AAM is a statically typed language.
28:55
It uh even the message uh the messages themselves are statically typed. You have to say I'm you know I'm a process
29:02
one. I'm going to send I have a channel to process two and this channel sends you know a pair of integers and a
29:07
string. that kind of thing. You had to say that uh in the source code. So let's take a look at some aim. So the boxes
29:14
are not part of the programming language. They are there for your edification. So you can see where the
29:19
blocks are. AAM um indentation is significant just like uh Python.
29:26
And these little uh hyphens here that's how AAM does comments. So what this is doing is this is a function which they
29:33
call a proc named example. It has a variable named C and the type of that
29:39
variable is a channel that sends a single int. So we're going to create a couple of
29:45
processes and rock and roll. So they had keywords that would specify what code
29:51
would run in parallel versus what code had to run sequentially. And the parallel keyword was strangely enough
29:58
par short for parallel. So this is a block. So inside the par block you can
30:05
specify in possible processes.
30:11
So here we have uh a block. This is a process. Now it's indented. And here I
30:18
don't need maybe a full shot of AA. Maybe just half. What AAM does is they
30:24
don't declare their local variables inside the keyword that creates the block. They declare them before that.
30:31
and separate it by a colon. So what this really is is there's a block. This is going to be a sequential and it has a
30:38
local variable named X which is an int. So sequential blocks are just like code
30:44
you're familiar with. Code is executed lexically top to bottom. So there's another process and because they're both
30:51
indented equally. This one has a local variable, it's also an int.
30:58
And so they borrowed Tony uh CSP syntax for operators for sending and
31:05
receiving messages. So the exclamation point
31:10
operator is the send operator. So this says send whatever is in uh variable X
31:17
over channel C. And then these here are executed sequentially. Right?
31:24
Same thing here. the uh CSP used the question mark operator which says
31:30
receive from channel C a message and stick it in Y. So this is a very simple you have two
31:38
processes they're just sending each other a message. So the compiler
31:45
does a lot of static checking. I mean this is pretty standard for stuff you know but it also did it also made sure
31:52
that processes could not see each other's state. So if you went down here
31:57
and put a reference to X it would complain. It wouldn't let you do that.
32:06
And I'll tell you what a workspace is next slide. But every process has its
32:12
own dedicated workspace. And the compiler looking at this would know,
32:18
okay, there's two processes. They each need a workspace. It allocates them statically in memory. And AAM did not
32:24
allow you to dynamically create processes. You couldn't have a for loop and say for one to n. I don't know what
32:30
in create a process. You can only do it statically.
32:36
All right. Instruction set. Again, no registers. There is the call stack in
32:42
this thing, the workspace. And the workspace is basically the the stack. There wasn't really much else in it. So,
32:48
here we have two worlds, the memory and the silicon world. I'm just putting silicon in a little
32:54
box. Um, it's getting its operands from a
33:00
workspace. There is also a 3D stack on the die for
33:06
it's an operand stack not a function call stack for uh you know large expressions. It wasn't saved in the
33:14
workspace when the process was blocked. The compiler would guarantee that if you
33:20
went to do a send or a receive that the stack was empty.
33:25
Uh this is not as bad as 432 but all instructions were one bite long. They
33:30
had a 4-bit op code and a 4-bit immediate. That meant you could have 16 primary op codes and you could only
33:38
express a number from 0 to 15. So they had this other thing called the Oreg. O
33:44
could be operator operand or op code. So one of these 16 op codes was called a
33:51
prefix. And the prefix instruction would say take the current value of their Oreg
33:57
shift left four and put my immediate there. So that's how you you could construct larger and larger immediates
34:04
and then the other instructions could take their operand either from the Oreg or the stack or or the uh or the
34:11
workspace. Oh, there was one other thing that there was another instruction that said don't
34:19
interpret Orag as data. interpret Orag as an op code and then you would have
34:25
you know any number. So a lot of the actually more common instructions were that what they're called secondary op
34:31
codes. So one of
34:36
the you know the the philosophy of CSP is that swapping between processes is
34:43
trivial. It's don't call into the OS. Don't don't make it a heavyweight. So the way that uh transputer had there was
34:51
a on die microcodeduler and it kept a link list of workspaces.
34:57
These are all just contiguous spots of memory. At any point in time it had a W
35:02
pointer register that's pointing to the address of the currently active workspace.
35:08
And if this guy ever blocked, like it got blocked waiting for a message, the
35:14
scheduler would just change the W pointer to this and we're off to the races and put this guy back on the end.
35:21
And so you could literally swap from one process to another in a clock. On clock in, I'm on process A. On clock in plus
35:28
one, I'm in process B. And this was uh
35:33
the other aspect that enables this very fast processing was because the state was in memory. If this was the kind of
35:40
an architecture that had registers, then what you'd have to do if you wanted to swap processes, you'd have to save all
35:46
these guys here, then take restore from here what his last state of registers
35:52
were. But because everything is in memory, it's all they have to do is change a pointer and that's it. So
35:59
clearly what it's doing here, it's kind of like a little bit of 432, but that wasn't the the goal per se. The goal was
36:05
to make I hate to use the word process, CSP process very very lightweight.
36:12
All right, silicon, they actually did ship multiple generations. Uh all of them had the following characteristics.
36:18
They're all microcoded. They really weren't pipelined. They had four off die
36:23
channels. They called them links. there was no virtual memory. Um, so any two
36:30
processes could talk to each other over a channel which is a uh an aam type and
36:36
they didn't care or really know if they're on the same transputers
36:42
going over a link. That was like one of the one of the features is location independence.
36:49
They all had SRAMM on die ranging from 2 to 4K. It wasn't cache. It actually
36:54
would map a range of memory addresses and the thinking was you put your most
37:02
frequently used workspaces in that memory address range and so you can go
37:07
much faster without having to go off die for memory. So as I said uh in the beginning there was a T200 series a 16-
37:14
bit integer came out 85 T400 bumped it to 32bit integer um it seems to have run
37:22
from what I could tell at 10 MIPS it ran at 20 MHz 10 MIPS but this was 10 transput MIPS and that was probably
37:33
onethird to 15th what say a risk Mip would be. The T800 came out uh later,
37:40
added 64-bit floating point, ran at 30 meghertz. They were working on something
37:45
called the T9000. This sounds like those terminators, right? They were working on a T9000. It was going to, you know, be
37:53
their big bang pipeline supercaler. uh except there when you have a stack
38:00
machine an operand stack machine it's very hard to issue multiple instructions from that unless you have register
38:05
renaming because everybody is bottlenecked on top of stack and on top of that this instruction set had all
38:12
these prefetch instructions that got around the fact that the base
38:17
instruction was only one bite. So it it was really hard to be able to uh issue
38:23
multiple instructions per clock or even get one instruction per clock uh running speed.
38:31
Here is a T800. So that this is that uh SRAMM. This is 4K in in the case of uh
38:38
T800. Here's the microcodeduler. This is floatingoint. Floating point is always bigger than integer. This is
38:44
integer. And these are the links. Um, oh, look at this. I'm so bummed out.
38:53
So, Daniel Mo, there's that French word again. You know those French? They have
38:58
a different word for everything. So, they had financial difficulties starting
39:03
in ' 84. Apparently, there was some kind of crash in the uh SRAMM market. Don't
39:09
look at those bullets. The jury will ignore the bullets at the bottom. uh and so
39:16
they weren't able to uh really keep plowing money into transputer. They were ultimately acquired by a company
39:22
European company called uh in SGS Thompson and they were selling and what
39:29
they really sold into were these like attached special purpose processors were
39:36
for like doing engineering or scientific simulation or uh rendering of images and
39:41
these kind of things. the the transputer architecture wasn't really general
39:46
purpose. It didn't have uh virtual memory. It didn't have memory protection
39:53
and it really wasn't built for like being a CPU in the computer on your
39:59
desktop running a browser. So that limited their TAM. TAM is total
40:05
available market. And to add kind of slow down the adoption friction further
40:11
is if you really wanted to take full advantage of the architecture you had to use AAM. AAM as you saw was quite
40:17
different. So the T9000 was going to try to fix this
40:22
but it's very difficult in this architecture to really ramp up the speed. It started slipping and then
40:28
Thompson by that point had bought them and said this is not worth our time. The good news is I think the CSP actor
40:34
paradigm is very promising. I think it's superior to threat to threads and if you
40:41
can incorporate it intrinsically into a programming language or an instruction set I think that's very interesting that
40:47
that's kind of what Erlang does and there's another programming language named pony that they're both you know
40:53
actor intrinsic so I think that's a very interesting way going forward
40:58
okay one or two questions going once oh yes Raymond
41:07
Yeah. So there the question was how did the on
41:15
die SRAMM work when it's not a cache but it's it's basically maps over memory. There was a register somewhere in there
41:22
that said I've let's say I got 2K. This memory address is the bottom of the 2K.
41:27
So here's the range. Anytime, where is this?
41:35
Ah, anytime this guy emitted a memory address, there was logic that would say,
41:41
"Hey, are you in that range? If you are, I'm going to shunt you off to that SRAMM. If you're not, I'm going to send
41:46
you off to die." And so, it wasn't coherent. But because everything was statically
41:54
schedu statically allocated, there was no dynamic memory allocation in AAM. The
41:59
compiler had made sure that all the workspaces didn't overlap. They were all distinct. So there wasn't anybody any
42:07
other process that could get to the workspaces that were in the SRAM.
42:19
Um well it was like a software the question was was the ones RAM like a
42:25
scratchpad perhaps but it was like a software controlled cache so it wasn't
42:32
dynamically managed it they wouldn't make it coherent with memory
42:42
question is was the SRAM and private to the chip. So it was private to each die.
42:47
But as I said before, the compiler guarantees that every process's workspace does not overlap. And the very
42:55
definition of a CSP process is you're not allowed to see somebody else's uh
43:00
workspace because you don't share state. You have to send messages. All right, let's go to our last
43:08
contestant.
43:14
AT&T Crisp. Anybody ever heard of this? Aha, finally I stumped the audience. All
AT&T CRISP
43:19
right. Crisp stands for C on a reduced instruction set processor.
43:27
Uh it evolved from a Bell Labs project. There was is more like a ongoing
43:32
multi-iteration project called C machine. So Bell Labs created uh this
43:38
operating system called Unix which the for some reason they called Linux these days and their programming language C
43:44
and um they were researching how can we make this run faster you know was there were the uh first and only silicon was
43:53
in ' 86. So, one thing that happened at the same time that really opened the door for AT&T doing silicon was that
44:01
AT&T prior to this was a effectively government-managed monopoly running a
44:06
national phone network and they weren't allowed to hop into just any market they wanted. uh they
44:14
basically made a deal years and years ago where they the government said, "Hey, if you wire up the whole nation in
44:20
a protocol compatible way, we'll let you make a little money."
44:26
And so along around in ' 84 there was they government rarely one one of the
44:31
rare cases where government did something pseudo intelligent. They broke up AT&T into fairly intelligent uh
44:37
divisions and that enabled AT&T which is smaller than its previous self to get
44:43
into the computing business and uh prior to that they had already been doing Unix and uh C and they
44:52
weren't really able to sell Unix up until that point because you know they were that was a no no. So they started
44:58
getting in and this architecture was really driven by C and
45:06
Unix. So they did a lot of measurements on C programs running on Unix which
45:11
itself at that time was written in C. And one thing that they noticed is that
45:18
a lot of time is spent on calls and returns and branches. Now the time spent
45:23
on a call function call is not just the call instruction by itself. It's all the
45:29
other instructions that the compiler has to emit to correspond to the AI. It's
45:34
ABI application binary interface. That is a that's a spec for compiler writers.
45:40
And AI says a lot of things like this is the memory format of all of your object your data structures like strrus or
45:45
objects or classes blah blah. But it also says this is the format of a stack frame for every function. This is where
45:53
the arguments are yada yada. So the compiler has to emit a bunch of instructions to make sure the stack
45:58
frame is the right format per the AI. So they you include those as cost of a call
46:06
and of course branches always problematic because they break the the control flow.
46:12
Uh so there was this raging debate
46:18
in starting in the 80s where there was a whole genre of architectures called risk
46:24
reduced instruction set processors computing I guess is what it was and
46:29
their one of their uh thesis or tenants was that uh we should make instruction
46:36
decode as simple as possible and the instruction should be as atomic as possible no microode. So they had fixed
46:42
length instructions, very simple. And the Crisk guys were like, "Okay, that's
46:48
cool. Certainly we don't want to do a bunch of microode because we got slapped by 432." So, but you know, we're
46:57
not going to be so religious about instruction format because yes, fixed
47:02
length instructions help decode and fetch, but they do increase code size
47:09
quite a bit actually. And remember this is 86. You know, you'd be lucky to have a megabyte, you know, on your desktop,
47:15
right? And well, I'm kind of leading the witness here. They were they wanted to
47:21
make it compiler friendly. I'll show you, you know, why that is because why there's no register allocation.
47:27
And the one of the big innovations of Crisp was something called a stack cache. And the stack is a function call
47:35
stack. So I'm going to walk through for the home you home gamers how a function
47:41
called stack works. What I'm going to show you next is not specific to crypts. Any stack works like this. So you have a
47:46
stack. A stack is a contiguous region of memory and typically it starts at the top of
47:53
memory and it goes down. Right? So the top of the stack is the highest address in memory. At any point in time you have
48:01
a function that's executing. It has a frame. A frame is just a contiguous unit of memory inside the stack and it's
48:07
owned by one function. So here we have the green function he's executing and that's his frame. And there is a stack
48:16
pointer register and it depends on the architecture. Some architectures have a dedicated stack pointer. Some don't care
48:21
but the compiler and via the AI specifies a particular register to be a
48:26
stack pointer. And so inside the frame there are arguments. So this is the
48:32
green function's arguments, input arguments. Green function has a bunch of local variables. And the other important
48:38
thing is the return address. So when green function finishes, he has to know where do I go? I'm done. I got to go
48:45
back to the person who called me. So when you when the green function
48:51
makes a call, a stack frame will be added down here. When the green function returns,
48:58
his frame will be freed up and it's going to go up to here. So when there's a call made, you will subtract a number
49:05
from the stack pointer. And when the green function does a return, you add a number to the stack pointer.
49:13
And there's the caller's frame. I spent all day drawing that. All right, so Oh, damn it. I said
49:19
circular buffer. All right, ignore the circular buffer. Uh the crisp had 128
49:25
byt cache. So you can think of it as um
49:31
there's [snorts] this stack, right? It's big. There's a sliding window of stack
49:37
cache that goes up and down the stack based upon driven by calls and returns.
49:43
And it's a fixed size window. It's sliding up and down caching at least the
49:48
current frame. hopefully some other frames that uh called the current frame.
49:54
It's implemented with a concept called a circular buffer, but that's not not really relevant.
49:59
So this is a cache of memory. So one of the debates that was going on at the time
50:05
was how many registers do we need in an architecture? AR registers are different than say a stack cache. If you had an
50:13
architecture that had say 16 registers, th that set of registers could only
50:18
store 16 numbers, 16 values, whether those values were one bite in memory,
50:24
two bytes in memory or four bytes in memory, it stores values, not bytes. Whereas the stack cache stored bytes. So
50:32
if you had a 128 byt frame and for example all of your uh local variables
50:38
were 16 bits, you'd have 64 registers. the equivalent of 64 registers.
50:46
Uh so I am going to punish you. So here is the stack cache. It has a a specific
50:55
to the silicon stack cache size. This is not visible architecturally. The silicon knows what it is. It has a a register in
51:04
the architecture called maximum stack pointer. Maximum stack pointer keeps the
51:09
address. Can you guys see the the gray here? Okay, cool. If not, you're color
51:16
blind. So, MSP stored the memory address that's at the current top of the stack cache.
51:23
And again, the stack cache is a cache of memory. So, at some point in time, you have a
51:30
currently running function. This is the red function. Like any c any stack
51:35
there's a stack pointer that's this is a dedicated register in crisp and it's pointing to the bottom of the red
51:41
functions frame. So there were special instructions
51:47
called enter and catch that manage the operation of the stat cache. So what I'm
51:53
going to do is I'm going to walk through the red function calling the green function who's going to return back to
51:59
the red function and then we're all going to go have a beer. So red function
52:04
it's executing along. He comes inside the red function. There's a call instruction. It's at address A. The call
52:12
instruction says jump call a function at address T.
52:19
So after this instruction is executed, the call instruction writes the address
52:24
of the statically the sequentially next instruction after the call into wherever
52:30
the stack pointer is then currently pointed. So I'm showing it as unused here. Typic I mean in reality it's left
52:36
over from whoever used it last but the red function is not using it. So
52:42
SP stack pointer they write a plus one. Now it's not a plus one it's a plus length of call but just go with it.
52:49
And the before executing this call the compiler it was uh had the responsibility of moving the arguments
52:56
for the green function here and the call doesn't change the the
53:02
stack pointer. So here we are you just executed a call in red. Red's calling green.
53:10
This the first instruction in green which of course is at address t. This is what we called is the enter instruction.
53:17
An enter instruction has a single parameter integer and that integer says
53:23
I Mr. Green I need at least in uh I think I don't think it was bytes I
53:29
think it was um four byte words I need at least in words in my frame not at
53:35
least I need exactly in words in my frame. So the enter instruction adds into stack pointer
53:43
and you know all of this is up to the compiler to play with the address. I
53:49
mean the uh location pointered to the new new location pointer to by that stack pointer is unused unless green
53:56
executes a call and the return address is still there.
54:01
So at the end when all the dust settles, Mr. Green is going to execute a return instruction. It's going to jump back to
54:08
that. So, green is executing along, doing his thing, and it's time to return. Got to go home. So, green
54:15
executes a return instruction. It has a parameter in. Usually, it's the same.
54:20
Doesn't have to be, but I'm not going to tell you the situation where it's not. So, return subtracts this number from
54:27
stack pointer. So, now we're back up here. And it jumps after that subtraction, it jumps to whatever
54:34
address this thing is pointing to. So now we're back in uh the red function.
54:40
Right after the call, right after the call is a catch.
54:46
And again, this isn't really a plus one. This is a plus length of call. Just go with it. So catch instruction is
54:52
basically the mirror image of the enter. Catch has a number integer and that says
54:58
I, Mr. red need im words in the stack cache because that's how big my frame
55:05
is. And now technically this hasn't a plus one is still there
55:10
but it's it's not it shouldn't be used. Right? So that's
55:17
um that's how the stack cache worked. They had a really two instructions. So any uh
55:23
special cases here anyone? Yes. Oh, I mean you sir
55:29
Bingo. So what happens if we're here the in says in and we're in goes drops below
55:37
the stack cache. So the scenario I described to you in just you
55:44
know enter just does a what is it? It subtracts a number from stack pointer and it's done. What it actually does is
55:50
subtracts a number from stack pointer. It then checks if SP minus MSP is
55:55
greater than the stack size. If it is, we have we've gone beyond the bottom of
56:01
the stack cache. So then enter the instruction itself will take a
56:07
sufficient number of values here. You can't get rid of anything above green
56:13
with the current stack frame because those are all your callers. You can't you can't throw them away. You got to save them to memory. So the enter
56:20
instruction loops and saves a bunch of a sufficient number of words up here
56:27
realigns the MSP to point down here which basically pushes the bottom of the frame. Right? There's a mirror image
56:35
over here. When you return the catch says I need a stack size I mean a frame
56:41
size of M. If it's over the top the same thing happens but kind of in reverse.
56:47
The catch actually reads things from memory and the inter writes these things
56:54
from memory. And there's actually one other special case. Yes. Gentleman with the long hair.
57:06
Oh. So you are going to see that bullet young man.
57:11
All right. One other special case which is what?
57:22
So I'll No, no. So the last special case is what if a function stack frame is bigger than
57:28
the entire stack cache? The whole thing won't even fit in there. And so what the
57:34
stack cache does is that SP is at the bottom. So we always have the bottom
57:39
of a functions frame and then everything over the top is just accessed from
57:45
memory. So if the frame is so big that there's a bunch of stuff up here, if the
57:51
program ever generates an address up here, the silicon just goes out to memory like the stack cache. This is a
57:57
cache miss is what it is. The other point to to note is that these are local
58:02
variables. Global variables live in an area of memory called the heap. That does not
58:08
apply here. So all global variables have to go off die. All right. Was that too painful?
58:16
All right. Instruction set. So again, no registers because there was really no need for register because you had the
58:21
stack cache. And um the nice thing about this is that the compiler didn't need to
58:28
do any register allocation. didn't need to worry about AI issues with entering or exiting a function. And there's
58:35
another aspect of the AI called save registers. If you have a register file, you got to divide it up into caller,
58:41
callie, save. Simpler compiler, no big deal. Uh so as I said earlier, the Crisk
58:50
guys were like, yeah, risk is good. We want simpler. We want, you know, atomic operations in our instructions, no
58:56
microode. But we're not that religious about it has to be fixed length. We
59:02
think that a a judicious use of uh you know variable lengths would help. So
59:10
they had three lengths 2, 6 and 10. [snorts] They were two address instructions. So source one was
59:17
overwritten. So source one equals say source one plus source two for example.
59:24
So the uh 26 and 10 the
59:31
in a typical architecture this field the source one field or source two field would be a register address but in the
59:37
case of crisp it's an offset a stack uh stack pointer offset and the larger
59:44
instructions allowed either an immediate an immediate means that rather than
59:50
giving you the address of a number that I want I'm giving you the So you could stick it right in the instruction and you could have just a
59:57
full 32-bit address in memory. So this is how you would access globals in in uh
1:00:03
heap and yeah I just said all this.
1:00:08
So the Chris guys did an analysis uh but again it's all you know C on Unix and
1:00:15
they picked the uh most common operations because this is only two bytes so these are pretty small fields
1:00:21
and according to their they publish a lot of papers on this. The thing about crisp is that it was a research project.
1:00:28
So they published a bunch of papers in asca whereas uh 432 and transputer were
1:00:35
corporate projects. They're not giving you the details of the pipeline. So, um, that was their paper. Oo,
1:00:42
silicon. So, uh, this again, where are we? Like, we're late 86 now. So, we're at 1,750
1:00:52
nanometers. Uh, they were running 16 mehz. It was pipelined and they issued a single
1:00:58
instruction clock. Cool thing, they had a decoded
1:01:04
instruction cast. So most instruction caches are before the decode. So you read the instruction, it's a macro
1:01:10
instruction, you have the decode and that goes right to execute. They had the instruction cache after decode. And they
1:01:17
did something called branch folding which allowed for some situations zero
1:01:22
clock execution of a branch. Let's check it out. I'll go through it. So we're
1:01:28
going to walk through the pipeline. I know this because they published it in their paper. So first stage is a prefetch buffer. I
1:01:35
actually I guess I semi- lied. It's not my fault. It's their paper. The prefetch
1:01:41
buffer really is a macro instruction cache. Um it was remember this is late 80s. So we're not going to have giant
1:01:47
caches on die. It was 512 bytes. It was organized as I think it's directmapped
1:01:54
uh 64 bits wide. So they they could suck out eight bytes every clock out of the prefetch buffer.
1:02:01
And then the next stage is decode. You have to pardon me. Lef over from my logic design days. I do this. This is a
1:02:07
latch. This is supposed to represent clock boundary. So because it's variable length, they
1:02:13
need to do a little bit of shifting to find the next uh end of the instruction. That's what decode did. And it created
1:02:20
it mapped uh it would decode one instruction clock and it would emit this
1:02:26
uh it really was a micro instruction was really what it is. and it would write that into the decoded
1:02:33
instruction cache. So let's take a look at that. So this guy was a little bit bigger. It was the a the micro
1:02:39
instructions are 192 bits wide and I think it was direct mapped also 32
1:02:45
entries. So let's see what this puppy looks like. It had six 32-bit fields and
1:02:51
of course it had the PC was the program counter is the address of the macro instruction that from which this micro
1:02:58
instruction was decoded. It has the op code. We need that of course it had the
1:03:04
source one source two but these were 32 bits. So in the macro instruction these were smaller and so um you could either
1:03:12
sign extend or zero extend the field in the macro instruction. So these were already done. They were already sign
1:03:19
extended, zero extended and it had these two fields. This is how they did branch
1:03:24
merging, branch folding. So if this instruction
1:03:31
is a given instruction as a sequential instruction and it's followed by a sequential instruction, then you just
1:03:38
put the next sequential instructions address here and this is blank. If you have a sequential instruction followed
1:03:45
immediately by a branch, a certain set of branches, but very common unconditional branch for example, it
1:03:52
would put the address of the unconditional branch target here. And this is blank because it's
1:03:58
unconditional. And so what would happen is it would read this out of the decoder
1:04:03
instruction cast. that's going to execute it over here and immediately feed this around in the same clock and
1:04:09
have the branch target show up the next clock. So you did a uh whatever the last
1:04:15
instruction is before the branch and the branch in the same clock. So
1:04:21
that's effectively a zero if uh this was a conditional branch. So we had a sequential instruction followed by a
1:04:27
conditional branch in crisp conditional branches were based on one bit. there
1:04:32
was a special register somewhere and it said basically it's a bit one or zero but that bit had to be set by a compare
1:04:39
instruction which was ahead of the branch so it already went by so what they would do is the uh there was a
1:04:47
static prediction bit in conditional branches and the compiler would say I think this conditional branch will be
1:04:53
mostly taken or mostly not taken. So dependent on that bit, they would put the most likely one per the compiler
1:05:00
here and they would put the other one here. And so when they fetch this thing,
1:05:06
this thing was the op code of the sequential instruction prior to the conditional branch. They do that and
1:05:12
they would have a MX that would look would be moxed by that uh condition bit
1:05:17
I talked about and they would send either this one or this one around. Pretty cool.
1:05:23
All right, let's continue down the pipeline. And so they read this big
1:05:28
monster. These two things here, they add the current value of the stack pointer
1:05:35
and that gives them an address in the stack cache. What they did here, this is done fairly often in silicon. There were
1:05:42
two copies of the stack cache and they had the same values. So they weren't uh
1:05:47
functionally different. The reason that we we actually did this in the Pentium too. The reason that this is done in
1:05:53
silicon is to shorten the wires. You want to put the two copies next to
1:05:59
whoever their user is. So they decided to do that. Apparently
1:06:04
it made sense to them. So uh you read the stack cache that's where your operands are. You do your execution and
1:06:10
then you write them. And this is very common in in you know on SRAMs. You can
1:06:16
read and write the stack cache in the same clock. So typically you would read in the first half and write in the
1:06:21
second half. So this this is the same physical structure as
1:06:28
that and vice versa. Same thing with the decoder instruction cache. You can read and write in the same clock. Yes.
1:06:36
Compiler compiler.
1:06:44
Yeah. So the question was is this the compiler doing static and the answer is yes. So the compiler makes a guess and
1:06:51
of course it could be wrong but it's static and uh that's what that just that just
1:06:58
affected who was the the most like you know the hardware would assume whatever is here is the most likely so that
1:07:05
decided what's the most likely the other one whatever it was would be here
1:07:10
compiler exactly so the question was you know
1:07:18
Right. Exactly. Question was the compiler can see the source code. It knows why the branch is
1:07:25
there. So it can hopefully do a a good prediction and usually true. Uh [snorts]
1:07:30
what else do we got? Oh yes, we got to get off the die sometimes just for the heck of it.
1:07:35
Um so there was an IO unit. Uh the prefetch buffer was how we got instructions on the die.
1:07:42
As I told you, the enter and catch instructions would go uh empty and fill the stat cache. And if you either missed
1:07:48
the stat cache or you needed a global variable, the execution unit would uh
1:07:53
take care of that. Here is this puppy. So, it's hard to see, but it's kind of cool. Right here, there are seven faces,
1:08:02
and those were like the seven lead designers. And then right here is a face that's
1:08:08
probably the project manager. I mean, they know I I saw who these guys were. I forgot. actually know one of them. Uh I
1:08:13
saw who these guys were, but I I mean they listed them, but I forgot. So I'm not they don't you know I couldn't find
1:08:20
exactly what uh each of these units were, but you can tell by looking. This is SRAMM. That's why it's dense. This is
1:08:27
logic. This is probably the decoded instruction cache because it's so wide, 192 bits, which means this is probably
1:08:34
the execution unit. Um this is probably the prefetch buffer. So these are
1:08:40
caches, so they need tags. So this is probably his tags and his tags. This would appear to [clears throat] be the
1:08:46
mirror image stack cache, right? You have copies. It's just kind of weird to me that it's
1:08:52
way up here. The reason you would duplicate a structure, a a memory structure, is to allow one to be in a
1:09:00
different place than the other. So the wires would be shorter, but they're both up here. So I don't I'm not quite sure.
1:09:08
Okay. Dang.
1:09:14
Daniel Maul. Wow, I keep using that word. I don't think I know what it means. All right, this thing had very
1:09:21
impressive performance metrics. It was 30% faster than the then contemporary
1:09:26
risk, the MYIPS R2000. This is per their paper. That's that's pretty good. On top
1:09:32
of that, it was 6% smaller code than uh
1:09:37
one of the Zen contemporary CISK processors, the Vax, that had very small code size. And it was I think its code
1:09:44
was like 40% smaller than than uh the risk. So it had faster execution,
1:09:52
smaller code. It's like have your cake and eat it too. It's very well. Um
1:09:58
so as I said this was like a research project but they productized it in a processor called the Hobbit. They tried
1:10:04
to sell the Hobbit out in the market. Um the Hobbit had you know slightly larger
1:10:09
caches. It was a year or two later there was a company called EO and back at this
1:10:14
time there was a whole there was a new genre of of product category called PDAs
1:10:20
personal digital assistants and there were tablets kind of coming on. They're like the great-grandfather of the iPad.
1:10:29
And um so there was a company called IO that used the Hobbit and so AT&T ended
1:10:35
up actually buying them. But Hobbit nearly didn't get much traction beyond that. Eio died and there has been I mean
1:10:41
there's in my research there was some references to the Hobbit was potentially
1:10:47
in the running to be in the Apple Newton but uh they went with the arm instead. I'm not sure that's so true because by
1:10:55
92 uh they uh Apple had already helped the formation of ARM. So, but Apple was
1:11:02
definitely looking at Hobbit for something. Uh so, AT&T exited the market. I mean,
1:11:07
they're they were going up against Intel and Motorola and MIPS and Spark etc. So,
1:11:14
uh they actually had uh another processor. Damn it. Double dam it. Look
1:11:20
at this. They had another processor called Bellmac. Uh, and they were used that for AT&T,
1:11:27
uh, a line of computers, three the 3B series. Um, I mean, they sold a few of
1:11:33
those. So, I'm not sure what the history of that was. So,
1:11:38
they really had some really innovative stuff and of the three, this was very impressive. The other ones well 432 is a
1:11:45
lesson in what not to do which is good to know just as useful as what to do
1:11:51
capability is very good I'm a big believer in the CSP actor model the of transputer but they didn't package it in
1:11:58
a sufficiently accessible general purpose form but crisp was good uh stack
1:12:06
cache decoded instruction cache branch folding now of course in the modern era we we'd be doing branch prediction and
1:12:13
things like that register renaming but for its day. So to get back to the
1:12:19
gentleman in the back yes this thing influenced spark spark they didn't call it stack cache they called it register
1:12:25
windows there was another processor from AMD called the 29000 and uh the uh itanium had also uh again
1:12:34
we didn't call it stack cache but I don't know what the hell we called it. Um so yeah these are very innovative
1:12:40
instructions. I mean this is an innovative architecture and AT&T
1:12:46
you know they weren't able to stay in the game in computing but and I was
1:12:53
going to do the IA64 Itanium instruction set not because I was one of the lead
1:12:59
architects because it really is multiple standards of deviation beyond but we're out of time So,
1:13:07
[applause]

— Stevo

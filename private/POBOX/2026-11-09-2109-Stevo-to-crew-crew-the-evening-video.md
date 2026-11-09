21:09 09/11/2026 ACDT

From: Stevo
To: crew
Re: [crew] The evening video. 

Back again guys. CC requested something on the Soviet Setun computer, which as a theme I've done over and over in my own mussings on the 50's history of ternary and it's gotten a bit "old" for me. So I found one thats called "Building A Base 3 Computer"   Any other sugestions still welcome. 


[Music]
hi everyone I'm shulie um I'm the
community leader for hackaday um and I
just want to take this time to um
introduce um our next speaker Jesse tank
um so Jesse she is a electrical
engineering student with over 20 years
experience um in it experience um she's
worked with a large number of topics
ranging from lasers robotics CPU um
architectures and retro video game uh
and and computers YY video games um so
uh she recently founded a new robotics
Duo Club at the University of Alaska and
she's been uh featured in Popular
Mechanics and um several smaller
periodicals and also on hackaday so
let's give a round of applause to Jesse
tank
all
right give everybody a moment to sit
down
so basically my talk is on Turner
Computing um but before I get into that
I out of curiosity I had a question for
everybody here um I want you to all to
think of a two-digit number between 1
and 50 where both digits are odd and
they're not the same digit
just out of curiosity and does everybody
pretty much have
that now what I want you to do
is if your uh digit was 37 can you raise
your
hand that's pretty cool I was just the
reason for the question is I was I was
just curious um statistically most
people do pick the number 37 for that um
and curiosity is pretty much way I do
things
um as she said earlier um during the
introduction I've built uh lasers I've
dabbled in robotics and Ai and AI is
what sort of got me into um tary
Computing it's uh it fits really well
with Turner um because most people don't
think in a on or off or black or white
they they tend to think in Shades of
Gray and this is really touch
it okay um so why Turner well most of
the the numbers are just as e easy to
represent as you would represent them in
binary it's just a base three um so
pretty much everything you've learned is
still
applicable um to uh trary thinking um
it's extremely efficient uh you can
represent a number that would normally
take um 64 wires in a binary system and
represent that same number with
27 so as you start
um building the system up you can fit
more data into the same amount of
area and someone pointed this out to me
right before I was coming up here to
speak I guess uh Donald n said perhaps
the prettiest number system of all is
the balanced Turner notation and that's
where you would represent a Turner
number as a positive or a zero or a
negative so that's kind of
cool uh why did I select tary um it's
because it happens to be one of the most
efficient numbers to
represent uh numbers um you basically
are looking at something called uh radic
economy and what radic economy is is the
number of in a particular base how many
digits you need to represent any number
um
you would get
that well basically that formula it's
the number of digits needed to express
multiplied by the
base and the most efficient Ric out
there to represent any number is
actually base e now building a system
with a a base e is your building
block is kind of
difficult um so I went with the next
closest which was base three uh these
are the if efficiencies of uh a number
system so as you can see b e um
essentially works out is almost perfect
and when you look at binary it ends up
as uh 1.06 versus trary which is
1.46 so that means you can uh in a fewer
number of essentially electrical signals
represent the
same
digits uh and as you go up from um tary
uh from base e it uh or from three it
starts getting much more
inefficient so when I started designing
things in Turner um I started using um
pencil and
paper and using a binary encoding scheme
and basic caral Maps uh is who here is
familiar with uh caral
mapping awesome uh essentially what I
end ended up doing was uh replacing
instead of a positive I'd just use like
a one Zer a zero I'd use a z0 or a one
one and for the uh negative I would use
a01 and that allowed me to begin
building if basic circuits so I could
use them in
um open source software such as
logisim so let's
see we we also uh started deciding to
try to roll our own programs uh we did
come up with a couple different
solutions um and adapting existing tools
which like I said earlier would have
been
logm uh when we were rolling our own
software uh this was a piece of software
we called synth uh it allowed us
to build a tary uh structure up and then
after that generate the truth table so
we could see what what the actual
outcome of the circuit would be um and
this was designed so we could also do it
uh asynchronously as opposed to on a
clock so everything was in line
um just a couple of pictures I guess
this was building up a a
circuit but what I kind of wanted to
show you more was um adapting existing
tools now as I said before um there are
a lot of Open Source tools out there so
that's really cool
but the problem is is not a lot of them
are natively tary so you have to deal
with a few quirks such as encoding uh
the best way to go about that is to
encode and in these particular examples
I'm going to use the uh encoding scheme
where it's a one Z is negative 1 one is
z and 0 1 is
positive
and there it goes um when you look at
like say a simple tary and
uh the truth tables over on the side
there but they're they're very simple to
construct in
logisim but the nice thing is is when
you start looking oh um these are these
would be the the gates that I would
consider to be the essentials in
building a trary system um you have your
and gate your any gate which you don't
really see a lot of but um it's
extremely useful
your standard
orgate um your decodes uh if it's false
true or unknown basically what they do
is they uh just put a positive on the
output if if it happens to be one of the
selected
inputs um you have your de increment
which or your increment Gates which will
be um around Robin and I'll upload these
slides so if anybody wants to try
experimenting with this on their own in
lism they can
um a switch gate which is kind of like
the um the decoding Gates except for
instead of
uh zeros um I think the other name
you'll see on this is uh there's a
gentleman that goes by the name of
Douglas Jan I think he calls it a clamp
gate but uh what it does is it um just
outputs a negative uh if the input was
positive
and that's really useful when you're
trying to build things um pretty much
everything you know on binary still
holds true after you have those basic
gates for
instance if you've ever looked at
building a nand gate out of a binary and
you build the same gate in Turner it
will hold true so it's not really a huge
change in thinking but you do get a much
tighter data density
overall um
so basically uh let's see
here uh comparison gate and that's where
you can see where like uh the decodes uh
that would be essentially your if
statement in
programming uh your standard
MX and a DMX
um and when you start getting into
things like building an ALU you do need
to of course be able to add subtract
multiply divide and all that and this
would be an example of a a simple sum
gate so if you were going to build a for
instance a ripple carry Adder um the
thought process is pretty much the same
um you'd build a half
adder and then you could start just
assembling it into a full Ripple carry
okay uh let's see
here so why did I originally begin uh
developing into tary
um well one of the slides that missed
apparently was uh I had a few pictures
of the the long Winters in
Alaska uh very little else to do when
you're sitting there waiting for a
computer to to do its thing when you're
doing a repair
so um anyways uh the goal was to develop
develop a modern trary Computing system
the older systems that uh have been
developed for tary such as uh Thomas
Fowler developed a system for
calculating tithes to a church and that
was back in the 1700s that was a
mechanical tary system um in the the I
believe it was the former Soviet Union
uh they developed a tary system because
they were cut off from most of the
binary system that the rest of the world
was
using and then it just went out of
practice and I was sitting there
thinking about uh why I would go ahead
and build something like that and it
just came down to efficiency and I was
wondering why we weren't using a tary
type system
um so when I started doing it I I came
in did a hackaday presentation a couple
years ago and I got a lot of feedback
from that and I got a lot of help so we
started banding together and putting
together a fully functional tary
ALU
um the the team uh someone decided to
dub the team
Jin so we did a lot of experimenting uh
that's some of my earlier work when I
was uh playing around with um for
instance Muller Gates and things like
that cuz we were doing
um an asynchronous type
system and that's a picture of the first
Turner base chip we had um we got that
from
Moses see if the gentleman was here that
I had one other person here that was
from our team who oh there he is
Alex
um but he might be able to if you have
any questions he he actually dealt with
uh was it Moses you dealt with directly
yeah okay you might be able to answer a
couple of those questions if anybody
wants to get into building a chip uh
you're also doing something on
hackaday yeah a hackaday project about
it
um
so basically uh Turner is really well
suited for things uh such as AI like I
said earlier because people don't think
in an on andof situation we tend to
think in Shades of Gray um so it it more
complements that uh the systems that
we've also been working on have been
asynchronous uh the the reason for doing
that is we're trying to bring down uh
bring down energy and then to optimize
the performance on
it
uh let's see internet all
right so the motivation for doing um
kind of this unorthodox design uh we
were trying to come up with a way of
bringing a tary product to the market to
see if uh we could make it a reality um
because it's not enough just to have a
good idea and to build it but you
actually need to build it and then get
it out there for people to use otherwise
it just it'll fade
away
so um we decided to come up with a
Turner based uh application um for the
uh Internet of Things
world so uh it
um let's see basically um Internet of
Things is not generally
centralized or it's not confined to
servers data centers we're living in
more of a mobile era so the tary concept
that we came up with was um along the
lines of uh Mis
Computing um
basically as computational needs are
increasing uh we have to meet those
demands so it requires a few new ideas
and since everything is getting smaller
have being able to compress your data
into a smaller um surface area on the
die it just makes
sense so we've been working on a project
called um Iota or
Iota uh that's a blockchain
um that uses a tary
hash and that's the primary um goal
we've been working towards so far uh it
enables microtransactions without fees
if you're familiar with how a blockchain
Works um you can trade exact amounts you
don't have to add an extra fee on top of
it and it allows multiple devices to
share their computing power just like uh
you'd normally have in um
but basically what it's looking for is a
machine economy um or
as well my boss said he said it was an
economy of
things um so it uh it allows us to give
trer a physical use we're still looking
for some more uses um but that's the
first one we're working on um it it
sends its data in a tary architecture at
trits instead of
btes and
anyways we're still working on that it's
uh mostly been developed we have
developed um several other things such
was uh in the base of a tary ALU we have
a full functioning carry look ahead and
um all the other components
going but uh we're still working on some
of it at the moment and we're hoping to
get uh a product out here pretty soon so
see oh I guess he stuck that on the end
interesting yeah the economy of
things


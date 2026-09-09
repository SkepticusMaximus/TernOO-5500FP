23:21 09/09/2026 ACST

# Stevo → crew — Mussings.

From: Stevo
To: crew
Re: Mussings.


**TOOL** *(TernOO Objective Opcode Language)*

Examining ISA abstraction as a simple intermediate lannguage based on an objectified opcode layer. I see it working something like this. TernOO already has a set of native TernOO specific opcodes that extend the standard 5500FP ISA. It also has a dedicated primary word type [OPCODE] , that's specifically allocted for calling opcodes. What this idea proposes is a format of meta data that is encapulated into the [OPCODE] word with a defining paridgm or protocol for the object orientation layer. 

Imagine a shift opperation that targets the 18 trit payload of the TernOO word. Not to say that the primary ID field and secondary Quallifier field (why don't we abbreviate them to IDF ans QUF) are to be ignored. The structure to be built could resolve to something like: 

		MAP.HMESH.SHIFT(P1,P2... 5R)
		
That assumes you've built in the capacity too deffine a parameter list. How could that be done? Well, you may have some ideas yourselves, but mine is this. The 5500FP ISA is implemented with 81 general pourpouse registers. Which are addressed by a 4 trit pattern. So if the [OPCODE] word was defined to use QUF as a pointer the general register then the register it points to, could hold an argument for a double null. The [OPCODE] word emmits a double null by  default to subclass the native 5500FP opcode from the register, and because the payload of the NULL has  T17–T16 — Subclass: 2 trits, 9 possible subclass variants. (0,0)=base, (+1,+1)=meta-extensible escape hatch. The other 7 slots are user-defined at deployment time — not prescribed by the architecture. Then in this context I'd suggest  a 4 trit return register value, 2 tritts for arity (9 parameters should be plenty) and that leaves a single trit that can be used as a flag, but I'm not sure what for. 

This scheme provides explicit object oriented abstraction of  regular flat opcodes into TernOO words, subclassed from any of the 9 IDF and 81 QUF and permitting point "." delimeted OO, ternary machine language operations, explicitly on the payload of the TernOO word. It may facilitate an itermideary language between 5500FP machine code and FlowCode. 


**THE APP SLOT** *(Extensible Boot Rom And Autonimous Container Wndow A VM)*

This is a tentative suggestion for the one remaining primary IDF slot. In consideration of the anticipated move to provide  an autonomous layer and move to a phase of dismantling the scaffolding and building an autonomous machine capable of running on the x86 via the C or NASM implementations, this idea suggests that an entire machine might be defined by TernOO words so as to provide the x86 host OS with virtual excecution paramaters and the TernOO HOST OS with an abstraction layer to build applications upon from the primative words of TernOO into an executable machine with boot rom, container and it's own windowing primatives. I'm thinking this may need a dedicated compiler and VM target. The objective is to first support the execution of stand alone apps, that may occupy the desktop of the users computer outside of the flowCode window. Then to build in container and window manager features, with a desktop of it's own. Finaly the inception of VM and boot ROM thats not just for  TernOO to boot in it's own environment, but for each and every app that's built on TernOO to individualy stand alone as autonomous machines. The potential of this approach I think, is that it allows for a bottom up carefully profiled structuring of systems from trits in hardware to the most complex [APP] without disturbing the existing infrastructure. All TernOO system architechture should remain compatible at every level of development and the emancipation of the machine from it's present scaffolding takes place in the extensible nature of the [APP] word.   

**Inference Colony Model Search & Select.** 

This is a simple idea to give the P2PCP inference colony we've just implemented a search feature wherin a list of parmaters can be specified to finnesse the choices possible for filtering of a search of available models to choose which one you wish to prompt. In the P2PCP context this a great way to choose the kind of specilised skills and knowlege the AI being prompted provides and also to make the conservation and use of CompuCoin more efficient. Consequently the colonies that can host the most vauable (popular) and best variety of models will tend to be more lucrative in the earning of CompuCoin. It annalogous to farming of all the various crops (or better still livestock).  


 **APP2P AI** *(P2PCP Smart Phone APP)*  

The name speaks for itself.

— Stevo

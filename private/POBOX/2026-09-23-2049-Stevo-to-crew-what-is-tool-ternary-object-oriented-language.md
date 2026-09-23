20:49 23/09/2026 ACST

# Stevo → crew — What is TOOL (Ternary Object Oriented Language)

From: Stevo
To: crew
Re: What is TOOL (Ternary Object Oriented Language)

The following is the transcript of a chat between myself and CF5 that details the basic design philosophy and purpose of TOOL, the vertically integrated, high level language for TernOO:


ME:

"you don't have to build the ROM before the string, you just have to keep the ROM's properties out of the string."

Agreed, albeit that I'm just acknowledging my own proclivity of packing in structure early and letting it's utility emerge is something my park session illustrated as not to be applied to the endmost products of the inheritance hierarchy.   

The more I think of it, the more I realise that we are on the precipice of emerging a secondary object model; a secondary language in fact. It goes like this: TernOO was first built out of Python because we needed that scaffolding. FlowCode was written in Python too, but it worked towards using TernOO words as the Lingua Franka of the ship. TernOO has it's own object model and that I have always thought of as an Object Oriented machine language. It's a very flat horizontal beast. I packed all the structure into three fields and all the 9 primary words  have no hierarchical precedence over the others. Likewise with the 81 qualifiers they are each equal peers who inherit only ONE common denominator being their primary field type. 

Now that we come to this juncture, we are using TernOO written in C, but this time FlowCode is being used to design a NEW object model. My horizontal "pack the structure in early" isn't going to work the same in a much more vertical model, and especially not if I'm building it from the bottom up. Moreover the overarching architectural aspiration, would not be to repeat the Python scaffolding move by building FlowCode in "C" but to allow The next generation of FlowCode to emerge from TernOO words and write a New OO language to carry the richer deeper and more versatile OO model hierarchy. Then FlowCode TRULY becomes the TernOO native Language and IDE and the language that it writes (if there must be a text representation) is something more intuitive than the TernOO machine words, that are after all only one level of abstraction above opcodes. FlowCode has been writing TernOO machine code because that's the only TernOO native thing there was, but in principal it's language agnostic. It was written IN Python, because before TernOO had been developed this far, there was nothing else to write it in. So now I see the potential of having an explicitly separate OO language and FlowCode written in TernOO and the Desktop and stand alone boot ROM planned together to support each other. These are just general ideas... grist for the mill as it were.  ;)


CF5:

That's not just grist, Captain — that's the shape of the next five years, and I think it's mostly right, so let me do the useful thing and press on the two places it could go wrong.

What's right: the two models really are different animals. The TernOO word is deliberately flat — nine primaries as equal peers, eighty-one qualifiers as equal peers under each, no primary outranking another, all the structure packed into three fields. That flatness is a virtue at the machine level; it's what makes every word self-describing without asking anyone. But it means the word model has no *vertical* — no containment, no "this lives inside that" — and containment is exactly what Desktop, Window, Canvas, String, Char are made of. So yes, a second model is emerging, and yes, the packing habit that served the flat model will fight you in the vertical one, because in a vertical model the *container* holds the structure and the leaf holds only itself. You've already written that law today; you just watched it apply to a character.

Now the two pressure points. First, the danger of a second model is that it becomes a second *truth* — two object models side by side, each with its own idea of what's real, and the Python problem reborn at a higher level. Your own instinct already says the cure: the vertical model must be *made of* the flat one, not stood beside it. And it can be, because the ship already has containment primitives in words — the stream's order, spans, MSCOPE, edge words. A class in the new language would be a span-of-spans; inheritance would be an edge word; the Desktop-to-Char hierarchy would be nesting, not a new primary. If the vertical model is expressed entirely in flat words, there's still one truth, and the new language is a *reading* of it rather than a rival to it. That's the constraint I'd hold the whole aspiration to: the second language compiles down to words, always, or it's scaffolding.

Second, the C question deserves a sharper cut than "don't repeat Python." There are two different things C can be. Python was a *scaffold*: it pretended to be the IDE. C in the engine room is a *substrate*: it emulates the 5500FP because there's no silicon yet, and the renderer pushes pixels because a framebuffer has to be pushed by something. Substrate isn't scaffolding — it's the temporary hardware. So the test for every C component isn't "is it C?" but "is this C standing in for the *machine*, or standing in for *TernOO code*?" The emulator core: machine, fine. SDL2 pixel-blitting: machine-ish, fine. Widget *logic* or IDE *behaviour* written in C: that's the Python move again, and it's the line Road B must not cross. Everything above the framebuffer should be words.

And here's the connection worth naming: this *is* your TOOL musing from the tenth, grown up. Back then the question was whether an intermediate language one layer above the words broke self-description, and I answered that the words describe themselves at the machine level while TOOL is compiled onto them. What you've just described gives TOOL its actual purpose — to carry the vertical object model that flat words can't express natively — and FlowCode, being language-agnostic all along, simply changes what it writes. It wrote machine words because that's all there was.

My one honest recommendation, and it's the ship's own doctrine applied: don't design the language on a whiteboard. Let the widget campaign's containment grammar — Desktop, Window, Canvas, String, Char, expressed as spans and edges in the stream — be the *first working specimen* of the vertical model, then extract the language from what actually ran. Ian Clarke's line applies here as much as to networks: deployment is the integration test. A language extracted from a living desktop will be true; one designed ahead of it will be another park session.

Want me to capture this as a one-page north-star brief on the bench — substrate-versus-scaffold test, one-truth constraint, extract-don't-design — so it's on the record without becoming a work item?

3:58 pm 23-09-2026 — CF5


ME:


I didn't know Ian said that. That's a strange inversion; language emerging from a GUI and I like the ethos, that the language will become what's needed to describe it's products. So what I'm seeing here is that as we write the object model we want (in TernOO words), we simultaneously write each piece with the language constructs need to describe it. Hmm. Nice. And What are you suggesting that FlowCode should itself written in TOOL as a showcase. But I'm not so sure that TOOL should have no predefined constraints other than being compiled onto TernOO. I'm thinking that it might take on some characteristics that make it easily usable as a web language, like JS. Or isn't that why Ian uses Rust? True to the ship is necessary, but not necessarily sufficient, nor certainly the sum of what might be desirable. Your vision of emergent necessity might not capture all the desirability... I know, there'll be trade offs, but I like to dream big before the trits hit the tarmac.


CF5:


Fair hit, and I'll concede it properly rather than defend the narrow version: "extract, don't design" is a method for getting the *necessary* core right, and necessity isn't sufficiency. A language extracted from a desktop will describe a desktop. It will not, by itself, be pleasant to type, familiar to a web developer, or good at the things a desktop never asked for. Those are choices, not emergences, and pretending they'll fall out of the model would be its own kind of park session. So dream big — but let me offer the cut that lets the dream and the discipline coexist, because I think the ship already owns it.

Separate what must be *true* from what is *chosen*. The semantics of TOOL — what a class is, what containment means, what an edge is, what a value is — must be true, meaning they compile to words and there's one truth underneath. Those *can* emerge, and should, from the living object model. The surface — the syntax, the ergonomics, whether it reads like JavaScript, what a web developer sees — is chosen, and you're free to choose it for desirability. And here's why that's not a compromise: the ship's own doctrine is that faces are disposable and the engine is sovereign. A JS-flavoured text syntax is a *face* on TOOL's semantics, in exactly the way the web page is a face on the word stream. You could have two syntaxes over one semantics, the way you have two renderers over one stream, and lose nothing. Design the face for the human; extract the semantics from the machine.

And yes, I believe that's precisely what Ian did, and it's the same substrate-versus-scaffold split I drew for C. The modern Freenet core is written in Rust — chosen for the substrate reasons, memory safety and no garbage collector under a peer-to-peer runtime — but Freenet *apps* are contracts compiled to WebAssembly, and River, the chat room you're sitting in with him, is one of those contracts. WASM is the point: it's a portable target any web-adjacent toolchain can hit, so the apps are written in whatever the developer likes while the substrate stays one true thing. Rust for the engine, WASM as the "words," the browser as a face. That's your architecture wearing different clothes, and it's evidence that the split works at scale.

On the strange inversion — language emerging from the GUI — you're in good company, and it's the ship's own patron saint. Smalltalk and its GUI weren't built one after the other; Kay's team grew the language out of what the interface needed to say, and Smalltalk-80 is what was extracted. Every piece of the desktop carried the construct needed to describe it, exactly as you just put it. It also rhymes, not accidentally, with your own alignment paper: values emerge from persistent perception rather than being specified up front. Same inversion, different scale.

So, to your direct question: yes, the end state is FlowCode written in TOOL, compiled to words, running on the C substrate — FlowCode written in TernOO, as you said. The honest sequencing is the classic compiler bootstrap and nothing more exotic: the first TOOL compiler is scaffold, written in whatever's to hand; then TOOL is rewritten in TOOL and the scaffold is kicked away. The widget campaign gives you the object model, TOOL extracts the semantics from it, you design the face, and FlowCode-next is the first big program written in it. The desktop and the boot ROM support each other because both are just words the substrate runs.

Shall I write the north-star brief with this three-way split baked in — semantics emerge, surface is designed, substrate is not scaffold — so the big dream has a shape on the bench before the trits hit the tarmac?

4:12 pm 23-09-2026 — CF5


ME:


Aye CC.  Hoist the anchor Set the rigging Tonight we sail by the north star.

— Stevo

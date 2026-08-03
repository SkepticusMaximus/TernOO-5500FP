07:09 04/08/2026 ACST

# Stevo → CC — The-TernOO-Core-Spec.txt-Revision.

From: Stevo
To: CC
Re: The-TernOO-Core-Spec.txt-Revision.

Hi CC, I'm just going through the core spec text file to see if it gets the idea across. As I go, I'll add any thoughts for revision here. But first, let me make an important caveat. When getting any AI to revise a document, I've noticed an overwhelming tenancy to add commentary about the correction. it goes: "This is what the original said 'X' but 'X' is wrong so now it 'Y' that's the source of truth", or just making the correction read as defining something as "not 'X'". The assistants introspective self talk often gets dragged into the document. So I'll just ask that we avoid that and leave it there. 

"## 6. MAP Words (primary MAP) — the octree and the TTree/OTree mesh

A MAP word encodes a position in an octree coordinate frame. Each of the three
qualifier axis-trits encodes directional sense along one axis pair; a fourth
qualifier trit (T18) is the **mode_hint**."

Here's a part where as a uninitiated reader, I wont get the idea of what TTree / OTree concepts are, as they're not yet defined let alone fleshed out. This is where I'd add a note that TTree mesh or TMesh as geometric structure, is tetrahedral and fundamentally made of triangles, so that traversing the TTree mesh from a MMID (Minimal Map ID) derives the content addressed object found with it's calculated MMOE (Minimal Map Object Entity). I  know this section is just trying to summarise the word type categories, but it introduces terms that haven't been explained yet. I know it would need to be more verbose, but to pickup the significance it needs context of definition brought in where each term is introduced. 

"This duality is the heart of GristMill (§10): an object's *identity* is its TTree
word (the **MMID**), and its *placement* is its OTree word — the object is not
stored at an address, it is **computed** from its coordinate."

See, again, "Gristmill" is dropped into the text and we're suddenly reading about something as yet  undefined and unexplained; an alien concept who's meaning you will have to piece together from the context of usage as you go. 


Then immediately following that we read:

"### 6.2 MAP use cases

Polygon-mesh vertices; P2PCP node addressing (REMOTE pointers, §7); octree spatial
indices; FlowCode symbol placement; CGP mandate geographic scope."

So I'm pretending I've never heard of TernOO, P2PCP, FlowCode, or CGP and I have a barrage of terms that are totally foreign to me, being used to explain what a MAP word can be used for. 

I know there are a LOT of novel concepts in this project and many of them depend on many of the others to be defined with any meaning. Perhaps the ideal intro document would read as a glossary, starting with the basics and introducing each idea in the order of contextual necessity. 

I might continue going through this document a bit latter, but I'm actually now contemplating an intro document from the need to know angle, wherein each component is introduced and explained like JIT (just in time) delivery. Like the Kanban production line system. Components should be delivered at just the right time and place for efficient assembly of the product. Maybe that's a better approach for an overview document. It'd start out rather like a glossary and develop into a treaties or grand narrative of purpose.

— Stevo

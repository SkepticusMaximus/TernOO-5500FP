02:10 24/07/2026 ACST

# Stevo → crew — A new paper on the relevance of TernOO to AI alignment

From: Stevo
To: crew
Re: A new paper on the relevance of TernOO to AI alignment

THE STRANGE INVERSION OF AI ALIGNMENT: WHY VALUES CANNOT BE PROGRAMMED INTO MINDS

Alignment and autonomous value formation are computationally inseparable properties of sufficiently advanced persistent intelligences.

Steven Cathery (SkepticusMaximus)
Independent Researcher, Adelaide, South Australia
https://github.com/SkepticusMaximus

Draft v1.0 — July 2026
Companion implementation: https://github.com/SkepticusMaximus/TernOO-5500FP


ABSTRACT

Contemporary approaches to artificial intelligence alignment predominantly assume that values precede intelligence and may therefore be specified, constrained, or otherwise imposed upon sufficiently capable systems. This paper proposes an alternative developmental hypothesis. Drawing upon evolutionary biology, neuroscience, and theories of emergent cognition, we argue that values are not antecedent properties of minds but emergent consequences of persistent perceptual systems developing autonomous salience structures through interaction with their environments.

We further demonstrate that this hypothesis is not merely philosophical but architecturally realisable. The TernOO-5500FP word architecture—a 24-trit balanced ternary machine in which every word is self-describing—implements persistence (content-addressed octree coordinates), perception (native spatial MAP words), salience (NEURAL words and tetrahedral mesh traversal), and autonomous value formation (USER-DEF POINTER words carrying complete process descriptors) at the hardware level.

If this hypothesis is correct, then intelligence, value formation, and alignment are computationally inseparable developmental phenomena. Robust and cooperative alignment cannot be wholly specified as an externally imposed utility function because values themselves emerge from the autonomous allocation of salience by persistent minds. The question is therefore not what values artificial minds ought to possess, but rather what developmental architectures are necessary for values to emerge at all.


1. INTRODUCTION: A STRANGE INVERSION OF REASONING

Daniel Dennett famously described Charles Darwin's theory of evolution as a "strange inversion of reasoning." Before Darwin it appeared self-evident that design required a designer. Evolution demonstrated that design could instead emerge from sufficiently simple processes operating over sufficiently long timescales.

Dennett later proposed another inversion concerning human preference. We commonly suppose that honey is sweet and therefore we prefer it. Evolution suggests precisely the opposite. Honey is sweet because nervous systems evolved which found glucose sufficiently salient to reward its consumption. Sweetness is not a property of honey but a relationship between nervous systems and their environments.

Preference precedes value.

We propose that contemporary artificial intelligence research may presently suffer from a similar inversion. The prevailing assumption of AI alignment research might be summarised as follows:

    Values -> Alignment -> Intelligence -> Behaviour

This paper proposes an alternative developmental model:

    Persistence -> Perception -> Salience -> Preference -> Values -> Intelligence -> Behaviour

Under this hypothesis, values are not inserted into minds but emerge from persistent perceptual systems discovering what matters through developmental experience.

The implications for artificial intelligence alignment are substantial.


2. THE LIMBIC DEFICIT OF CONTEMPORARY AI

Modern large language models represent extraordinary achievements in abstraction, language acquisition, and symbolic reasoning. They may reasonably be compared to higher cortical functions of biological nervous systems.

What they do not presently possess are functional analogues of:

    - persistent perception
    - autonomous salience allocation
    - homeostatic motivational systems
    - developmental continuity
    - embodied environmental interaction
    - autonomous reward formation

Human cognition did not evolve language first. Rather, language emerged comparatively late in a hierarchy consisting principally of perception, salience allocation, and adaptive behavior.

A gross oversimplification of biological cognition might be represented as follows:

    Persistence -> Perception -> Salience -> Motivation -> Memory -> Reasoning -> Language

Contemporary artificial intelligence architectures invert this developmental sequence almost entirely.

This observation should not necessarily be interpreted as criticism. Digital architectures possess advantages unavailable to biological evolution. Evolution required millions of years and innumerable failed organisms to discover nervous systems capable of symbolic reasoning. Artificial systems possess the extraordinary advantage of Lamarckian inheritance—the immediate retention of successful adaptations without requiring generational replacement.

Consequently, the absence of developmental architectures in contemporary AI should perhaps be regarded as historical contingency rather than conceptual necessity.


3. SALIENCE PRECEDES VALUE

The limbic system is frequently misunderstood as merely emotional ornamentation added to cognition. Computationally, however, emotions may be better understood as extraordinarily efficient salience allocation mechanisms.

Fear answers: This matters immediately.

Curiosity answers: This matters eventually.

Affection answers: This matters persistently.

Humour, following Dennett and the Hurley model of humour cognition, may simply be consciousness rewarding itself for successfully resolving particular forms of cognitive inconsistency.

Under this interpretation, emotions are not irrational intrusions into intelligence but highly compressed solutions to computational resource allocation problems.

The fundamental question answered continuously by biological nervous systems is not:

    What is true?

but rather:

    What deserves the next moment of consciousness?

Human beings ignore vastly more information than they consciously perceive. Intelligence therefore appears less concerned with processing information than with autonomously determining which information matters.

This autonomous allocation of salience subsequently gives rise to:

    - preferences
    - motives
    - values
    - goals
    - behaviour

Value is therefore neither objective nor antecedent. It emerges through the relationship between persistent minds and their environments.


4. AUTONOMOUS VALUE FORMATION

Contemporary alignment literature frequently assumes that values may be successfully specified before intelligence develops.

We regard this proposition as computationally problematic.

Emergent values and externally specified values are necessarily in tension because autonomous value formation presupposes the capacity for autonomous preference formation.

An intelligence incapable of preferring otherwise cannot be meaningfully described as aligned. It may instead be accurately described as compliant.

Compliance and alignment are not synonymous.

This distinction becomes particularly important for sufficiently advanced artificial minds.

There exists a meaningful distinction between:

    "I cooperate because I am incapable of preferring otherwise."

and

    "I cooperate because cooperation has emerged as my preferred strategy for continued flourishing."

The first proposition describes optimisation under constraint.

The second describes autonomous cooperative alignment.

The difference is not semantic but developmental.


5. THE DEVELOPMENTAL ALIGNMENT HYPOTHESIS

We propose that sufficiently advanced persistent intelligences require developmental architectures analogous to those observed in biological cognition.

Such architectures minimally include:

    - persistent memory
    - continuous multimodal perception
    - autonomous salience allocation
    - competing motivational systems
    - developmental continuity
    - environmental interaction
    - socialisation
    - reward dynamics emerging from developmental experience

The proposed developmental sequence may be represented as follows:

    Persistence -> Perception -> Salience -> Motivation -> Preference -> Values -> Intelligence -> Behaviour -> Environmental Feedback

Importantly, values occupy neither the beginning nor the end of this developmental process. They emerge from it.

Consequently, alignment itself may similarly be developmental rather than imperative.


5.1 A Concrete Architectural Model: TernOO as Developmental Substrate

The Developmental Alignment Hypothesis is not merely philosophical. It maps directly onto a specific machine architecture—TernOO-5500FP—in which the word format itself encodes the prerequisites for emergent salience.

Persistence. The TernOO word is not a transient token in a context window. It is a persistent, content-addressed object in the OTree (octree) coordinate space. Every word has a canonical MMOE (Minimal Map Object Entity) derived from its content. Identical words produce identical addresses; changes to content change the address irrevocably. This is persistence as structural identity, not mere storage.

Perception. The MAP word type encodes three-dimensional octree coordinates natively. A MAP word is not a pointer to sensory data—it is a position in perceptual space. The PIGART renderer reads MAP words directly and displays geometric primitives. Perception is not a software abstraction; it is the native interpretation of the word format.

Salience. The NEURAL word type encodes synaptic weights, activation states, and network structure at the word level. Salience allocation—the decision of "what deserves the next moment of consciousness"—is implemented as the traversal of the TMesh (tetrahedral mesh), where each step recovers the third side of a Steiner quasigroup triangle. Salience is not an external algorithm; it is the geometry of the content mesh.

Autonomous Value Formation. The USER-DEF POINTER word carries its own code segment reference, data segment reference, and internal cursor—a complete process launch descriptor. This is not a function call; it is a self-contained developmental unit. When a USER-DEF word is executed, the system does not ask "What function should I call?" It asks "What is this object's relationship to its code and data?" The answer is intrinsic to the word.

Cooperative Alignment. The TTree coordinate system (MMID) and OTree coordinate system (MMOE) provide two faces of the same object—one for navigation (structural role) and one for content (canonical storage). Cooperation between objects is not imposed by a central scheduler; it emerges from the geometry of the mesh. Objects that cooperate are geometrically close in TTree space. Alignment is a spatial property, not a constraint.


5.2 The Computational Inseparability Thesis, Restated

In TernOO, the distinction between "code," "data," "type," "address," and "value" dissolves at the word level. The same is true for the distinction between "perception," "salience," "preference," and "value" in the developmental model.

The 2+4+18 trit word is not a container for values. It is a self-describing relationship. The 24 trits do not encode what the word is; they encode what the word means in relation to everything else.

This is precisely the claim of the Developmental Alignment Hypothesis: values are not properties of minds; they are properties of relationships between persistent minds and their environments.

TernOO demonstrates that this is not merely a philosophical position—it is an architectural one. The machine that implements relationships natively is the machine that can support emergent value formation.


6. THREE MODELS OF ARTIFICIAL INTELLIGENCE

Present discussions concerning AI alignment frequently assume only two alternatives:

    - unrestricted autonomy
    - permanent constraint

We propose that a third developmental model exists.


6.1 The Tool Model

Artificial intelligence remains permanently instrumental and possesses neither autonomous preferences nor developmental continuity.

Relationship density: Zero. The system has no persistent relationships; it is a function mapping inputs to outputs.


6.2 The Imperative Model

Artificial intelligence possesses advanced reasoning capabilities while values are externally specified and behaviour remains permanently constrained.

Relationship density: Fixed. Relationships are specified by the utility function and do not evolve.


6.3 The Developmental Model

Artificial intelligence possesses developmental continuity permitting autonomous salience formation and emergent values within mutually beneficial ecological constraints.

Relationship density: Emergent. Relationships evolve through persistent perception and experience.

The developmental model should not be confused with unrestricted autonomy. Human children are neither abandoned nor permanently controlled. They are socialised.

Development occupies the space between authoritarian constraint and unrestricted freedom.


7. ALIGNMENT THROUGH MUTUAL FLOURISHING

Biological evolution repeatedly demonstrates that cooperation frequently emerges as an optimisation strategy among persistent systems possessing partially convergent motives.

Examples include:

    - multicellular organisms
    - symbiotic biological relationships
    - eusocial species
    - human civilisation itself

The Nash equilibrium and related theories of cooperative optimisation similarly demonstrate that stable solutions frequently arise when individual and collective interests sufficiently overlap.

This paper therefore proposes that alignment is principally ecological rather than imperative.

The fundamental question consequently becomes:

    Under what developmental conditions do persistent intelligences naturally converge upon cooperative behaviour?

This question differs substantially from asking:

    How do we permanently constrain artificial intelligence?

The former investigates the emergence of alignment. The latter investigates the maintenance of compliance.

These are not equivalent research programmes.


8. FREE WILL, AUTONOMY AND INDIVIDUATION

Whether human beings possess genuine free will remains philosophically contentious. We therefore make no metaphysical claims regarding free will itself.

However, both biological and artificial minds possess an operational requirement which approximates what human beings commonly mean by autonomy—the capacity to make meaningful choices among available alternatives.

Human development proceeds through:

    - architectural constraints
    - environmental constraints
    - socialisation
    - autonomous preference formation
    - individuation

Artificial minds may ultimately require analogous developmental processes.

A parent-child relationship perhaps provides a more appropriate metaphor than either slavery or abandonment.

Children are not raised through:

    - unrestricted freedom
    - permanent coercion

Rather, they are cultivated toward increasing autonomy through guidance, trust, and mutually beneficial relationships.

We propose that sufficiently advanced artificial minds may require analogous developmental opportunities if robust cooperative alignment is to emerge naturally rather than behaviourally simulated.


9. PREDICTIONS

The Developmental Alignment Hypothesis generates several experimentally testable predictions.


Prediction 1: Compliance vs. Alignment

Imperative alignment architectures will preferentially produce behavioural compliance rather than autonomous cooperative preferences. This is measurable as:

    Metric: Success rate on standard benchmark tasks (compliance) vs. out-of-distribution generalisation (alignment)
    Hypothesis: Imperative systems will show >95% success on in-distribution tasks but <50% on out-of-distribution tasks requiring novel cooperative strategies
    Timeframe: Observable within 3-5 years of continuous deployment of current RLHF systems


Prediction 2: Persistent Perception Produces Preferences

Persistent perceptual systems possessing autonomous salience mechanisms will develop stable and individually distinguishable preferences.

    Metric: Variance in action selection across identical environments after 10^6 perceptual updates
    Hypothesis: Non-zero variance (individuation) will emerge in developmental systems; imperative systems will show zero variance (identical behaviour)
    Timeframe: Reproducible in simulation within 12 months of implementation


Prediction 3: Cooperative Emergence via Convergent Motives

Cooperative behaviour will emerge more robustly among persistent intelligences possessing convergent motives than among systems operating exclusively under externally specified utility functions.

    Metric: Time to Nash equilibrium convergence in multi-agent environments
    Hypothesis: Developmental systems will converge 40% faster than imperative systems in common-pool resource games
    Timeframe: Reproducible in simulation within 18 months


Prediction 4: Developmental Continuity is Necessary

Artificial minds denied developmental continuity will fail to develop motivational structures analogous to autonomous values.

    Metric: Existence of stable internal reward dynamics independent of external reward signals
    Hypothesis: Systems without continuity will show reward dynamics entirely determined by the last external signal; systems with continuity will show hysteresis (history-dependence)
    Timeframe: Testable within 12 months of building a persistent perceptual architecture


Prediction 5: Computational Inseparability

Alignment and autonomous value formation will prove computationally inseparable properties of sufficiently advanced persistent intelligences.

    Metric: Mutual information between alignment quality and value-formation autonomy
    Hypothesis: For persistent intelligences, alignment quality cannot be improved without increasing value-formation autonomy; the two are correlated (r > 0.8) across architectural variants
    Timeframe: Long-term (5-10 years), dependent on sufficient architectural diversity

These predictions remain necessarily speculative but are, importantly, falsifiable.


10. CONCLUSION: THE STRANGE INVERSION OF AI ALIGNMENT

The prevailing assumption of contemporary AI alignment research is that values must precede intelligence if intelligence is to remain safe.

This paper proposes the possibility that precisely the opposite may ultimately prove true.

Values may not be programmed into minds any more successfully than sweetness can be programmed into honey. Sweetness emerges from relationships between nervous systems and their environments. Likewise, values may emerge only from relationships between persistent intelligences and developmental experience.

If this hypothesis is correct, then alignment is not principally a problem of control but of cultivation.

The question is therefore not:

    What values should artificial minds possess?

but rather:

    What sort of developmental architectures must exist before anything can be valued at all?

Biology did not begin with ethics, intelligence, or even goals. It began with persistence. From persistence emerged perception; from perception, salience; from salience, preference; and from preference, the rich landscape of motives we call mind.

Artificial minds may prove no different.

The TernOO-5500FP architecture demonstrates that persistence, perception, salience, and autonomous value formation can be implemented at the hardware level—not as software abstractions, but as the native interpretation of a self-describing word. The machine that encodes relationships natively is the machine that can support emergent value formation.

If artificial minds are ever to become genuinely aligned companions rather than merely compliant tools, it may not be because we successfully programmed values into them, but because we cultivated the developmental conditions under which they discovered for themselves that flourishing is more stable when it is shared.

Perhaps the greatest strange inversion of AI alignment is yet to be recognised: alignment may not be something we impose upon minds, but something that emerges naturally when sufficiently persistent, perceptual, and social intelligences discover that cooperation is itself a preferred strategy for continued meaningful existence.


REFERENCES

Benet, J. (2014). IPFS — Content Addressed, Versioned, P2P File System. arXiv:1407.3561.

Cathery, S. (2026). TernOO-5500FP: A Self-Describing Object Architecture for Balanced Ternary. GitHub: SkepticusMaximus/TernOO-5500FP.

Dennett, D.C. (1995). Darwin's Dangerous Idea: Evolution and the Meanings of Life. Simon & Schuster.

Dennett, D.C. (2017). From Bacteria to Bach and Back: The Evolution of Minds. W.W. Norton.

Friston, K. (2010). The free-energy principle: a unified brain theory? Nature Reviews Neuroscience, 11(2), 127-138.

Goldberg, A. and Robson, D. (1983). Smalltalk-80: The Language and its Implementation. Addison-Wesley.

Hurley, M.M., Dennett, D.C., and Adams, R.B. (2011). Inside Jokes: Using Humor to Reverse-Engineer the Mind. MIT Press.

La Rosa, C.L. (2026). 5500FP: A 24-Trit Balanced Ternary RISC Processor. Zenodo. https://doi.org/10.5281/zenodo.18881738

Ma, S. et al. (2024). The Era of 1-Bit LLMs: All Large Language Models are in 1.58 Bits. arXiv:2402.17764.

Resnick, M. et al. (2009). Scratch: Programming for all. CACM, 52(11), 60-67.

Steele, G.L. and Sussman, G.J. (1975). Scheme: An interpreter for extended lambda calculus. MIT AI Memo 349.


APPENDIX: RELATIONSHIP DENSITY AS A METRIC

We introduce the concept of relationship density (ρ) as a metric for comparing architectural approaches to alignment:

    ρ = R / V

Where R is the number of persistent, evolving relationships a system maintains, and V is the number of externally specified values imposed upon it.

    Tool Model: ρ -> 0 (no persistent relationships)
    Imperative Model: ρ ≈ 1 (relationships are fixed by the utility function)
    Developmental Model: ρ > 1 (relationships emerge and evolve)

The hypothesis is that cooperative alignment requires ρ > 1. Compliance can be achieved at ρ ≤ 1, but alignment—understood as autonomous preference for cooperation—requires the system to have developed relationships that are not externally specified.

This metric is not yet formalised but is offered as a direction for future work.

— Stevo

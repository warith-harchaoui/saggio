# Every initialism this repository uses, written out

[🇫🇷 GLOSSAIRE.md](GLOSSAIRE.md) · 🇬🇧 English

The rule this page serves: **nowhere an acronym that is not spelled out and
explained before it is used.** Each page expands the ones it leans on at their
first appearance, because a reader landing on one page has not read another.
This page is the whole vocabulary in one place, read by a contract test: an
initialism a page uses and does not expand is a failing build; an initialism
this page defines that no page uses is removed from it.

Some of these are French, some English, a few neither — `ISO` is not the
initials of the International Organization for Standardization, which is noted
where it appears below.

## Reporting and accounting

| Initialism | Written out | What it is |
|---|---|---|
| **GHG** | Greenhouse Gas | the GHG Protocol, the corporate accounting standard that splits emissions into scopes 1, 2 and 3 |
| **CSRD** | Corporate Sustainability Reporting Directive | the European Union directive that requires large companies to publish sustainability information |
| **ESRS** | European Sustainability Reporting Standards | the standards that say what a CSRD filing must contain; E1 is the climate one |
| **EFRAG** | European Financial Reporting Advisory Group | the body that drafts the ESRS |
| **SCI** | Software Carbon Intensity | the Green Software Foundation's specification for stating a software system's carbon per unit of work |
| **PUE** | power usage effectiveness | a data centre's total energy divided by the energy its computers draw: 1.0 would be a building that costs nothing to cool |
| **WUE** | water usage effectiveness | litres of water per kilowatt-hour of computing energy, counted on-site: it excludes the water used to generate that electricity. [WATER.md](WATER.md) explains what it does and does not say |
| **withdrawal** | — | water taken out of a river, an aquifer or a main. Not the same as consumption |
| **consumption** | — | the withdrawn water that does not return to the body it came from — mostly evaporated. It is relocated rather than destroyed, which is why the place and the season matter more than the litre |
| **blowdown** | — | the fraction of a cooling loop bled off because the salts left behind by evaporation have concentrated. The small, genuinely degraded share |
| **PCF** | product carbon footprint | a manufacturer's published figure for the carbon of making one unit of a product |
| **LCA** | life-cycle assessment | accounting for a product's impact from raw material to disposal |
| **AIB** | Association of Issuing Bodies | the European body that publishes the residual electricity mix |
| **PPA** | power purchase agreement | a contract to buy electricity from a named generator, which is one of the instruments a market-based figure rests on |
| **ADEME** | Agence de la transition écologique | the French environment agency, which publishes emission factors |
| **AFNOR** | Association française de normalisation | the French standards body |
| **ECB** | European Central Bank | whose published rates this package reads for a currency conversion |

## Standards bodies and legal citations

| Initialism | Written out | What it is |
|---|---|---|
| **ISO** | International Organization for Standardization | whose name is not an initialism of itself: it comes from the Greek *isos*, equal. ISO 14067 is the carbon-footprint standard, ISO 8601 the date format, ISO 4217 the currency codes, ISO 3166-1 the country codes |
| **IEC** | International Electrotechnical Commission | which co-publishes several of those standards |
| **EU** | European Union | — |
| **AI** | artificial intelligence | — |
| **GPAI** | general-purpose artificial intelligence | the EU AI Act's term for a model not built for one task; Annex XI is its technical-documentation requirement |
| **CELEX** | — | the European Union's identifier scheme for its legal documents |

## Machines and their counters

| Initialism | Written out | What it is |
|---|---|---|
| **CPU** | central processing unit | the processor |
| **GPU** | graphics processing unit | a graphics card or accelerator |
| **TPU** | — | Google's Tensor Processing Unit, a name rather than a category |
| **RAPL** | Running Average Power Limit | Intel's and AMD's on-chip energy counter, which is where a Linux power figure comes from |
| **NVML** | NVIDIA Management Library | the interface that reports an NVIDIA accelerator's power |
| **IPMI** | Intelligent Platform Management Interface | a server's out-of-band management channel, which can report whole-chassis power |
| **DCMI** | Data Center Manageability Interface | an IPMI extension that standardises that power reading |
| **MSR** | model-specific register | a processor register read directly, rather than through the kernel |
| **ABI** | application binary interface | the contract between a program and the kernel or a library it calls |
| **ISA** | instruction set architecture | the set of instructions a processor implements |
| **DRAM** | dynamic random-access memory | the machine's main memory |
| **HBM** | high-bandwidth memory | the memory stacked beside an accelerator's die |
| **FLOP** | floating-point operation | one arithmetic operation on a decimal number; TFLOP/s is a trillion of them a second |
| **ARM** | — | the processor architecture, a company name rather than an initialism today |
| **POSIX** | Portable Operating System Interface | the standard that makes a command behave the same on Linux and macOS |
| **CVE** | Common Vulnerabilities and Exposures | the public catalogue of security flaws, each with an identifier |

## Software and formats

| Initialism | Written out | What it is |
|---|---|---|
| **API** | application programming interface | the surface one program offers another |
| **CLI** | command-line interface | — |
| **GUI** | graphical user interface | — |
| **HTTP** | HyperText Transfer Protocol | what a web request is made of |
| **HTML** | HyperText Markup Language | what a web page is written in |
| **URL** | Uniform Resource Locator | a web address |
| **YAML** | YAML Ain't Markup Language | the file format this package's models and catalogues are written in |
| **JSON** | JavaScript Object Notation | a machine-readable data format |
| **CSV** | comma-separated values | a table as plain text |
| **SVG** | Scalable Vector Graphics | a picture described as shapes rather than pixels |
| **PDF** | Portable Document Format | — |
| **AST** | abstract syntax tree | a parsed program as a tree, which is how this package reads source without running it |
| **OCR** | optical character recognition | reading text off an image |
| **CI** | continuous integration | the automated build that runs on every change |
| **BSD** | Berkeley Software Distribution | the family of permissive licences this package is released under |
| **CC** | Creative Commons | the licence family; CC BY is its attribution licence |
| **RFC** | Request for Comments | the document series that defines internet standards |
| **WCAG** | Web Content Accessibility Guidelines | the accessibility standard; AA is its middle conformance level |
| **CLDR** | Common Locale Data Repository | the Unicode Consortium's database of how each language writes numbers, dates and names |
| **IANA** | Internet Assigned Numbers Authority | which publishes the timezone database |
| **UTC** | Coordinated Universal Time | the time standard every timestamp here is in |
| **IT** | information technology | — |
| **JIT** | just-in-time | compiling a program while it runs rather than before |
| **JVM** | Java Virtual Machine | — |
| **IR** | intermediate representation | a compiler's internal form of a program, between source and machine code |

## Machine learning, measurement and the cloud

| Initialism | Written out | What it is |
|---|---|---|
| **ML** | machine learning | — |
| **SSL** | self-supervised learning | training without labels — not the network protocol of the same initials |
| **KV** | key-value | the cache a language model keeps of its own attention keys and values |
| **MAE** | mean absolute error | the average size of a prediction's error, in the unit being predicted |
| **MAPE** | mean absolute percentage error | the same, as a share of the true value |
| **WCET** | worst-case execution time | the longest a piece of code can take, proved rather than measured |
| **WCEC** | worst-case energy consumption | the same question asked of energy |
| **RMS** | read memory size | how much of its input a routine actually reads, which is the size a cost bound should be stated against |
| **IF** | Impact Framework | the Green Software Foundation's tool for composing an environmental-impact pipeline |
| **AWS** | Amazon Web Services | — |
| **GCP** | Google Cloud Platform | — |
| **OCI** | Oracle Cloud Infrastructure | — |
| **ACM** | Association for Computing Machinery | the learned society that publishes many of the papers cited here |

## What is not an initialism here

Each with the reason, so that a page is not asked to explain a filename or a product's model number.

| Kind | Examples | Why |
|---|---|---|
| This repository's own page names | `README`, `LISEZMOI`, `STANDARDS`, `NORMES`, `ANALYSIS`, `ANALYSE`, `ANNEX`, `ANNEXE`, `JOURNAL`, `CHANGELOG`, `TRIGGERS`, `DECLENCHEURS`, `GALLERY`, `GALERIE`, `MEASURING`, `MESURER`, `USING`, `UTILISER`, `EXAMPLES`, `EXEMPLES`, `LANDSCAPE`, `PAYSAGE`, `INVENTORY`, `INVENTAIRE`, `BOUNDARIES`, `FRONTIERES`, `CONTRIBUTING`, `CONTRIBUER`, `CODING`, `SKILL` | They are filenames, written in capitals because that is how the file is named. |
| Product and model names | `H100`, `A100`, `B200`, `M1`, `M2`, `M4`, `HGX`, `SXM`, `SXM4`, `SXM5`, `GTX`, `EPYC`, `NVIDIA`, `CUDA`, `LLVM`, `XMOS`, `PCRE`, `PHP`, `SAGGIO` | A name, not an initialism a reader has to decode. `SXM` and `HGX` are NVIDIA board form factors; the vendor does not expand them either. |
| Research tools and venues, inside a citation | `PLATYPUS`, `OSACA`, `OTAWA`, `IACA`, `COSTA`, `SPEED`, `C4B`, `SHAP`, `FSE`, `ICS`, `OSDI`, `PLDI`, `TECS`, `ISSCC`, `SCOPES`, `SCP` | Every one sits next to a link to the paper or the tool, which is where a reader goes. A venue abbreviation in a citation is scholarly convention, not jargon. |
| Companies named in a cited list | `CAST`, `UBS`, `NTT`, `DATA`, `AFAS` | Company names. `NTT DATA` is the company's name. |
| Units, codes and identifiers | `GB`, `KB`, `MB`, `CO2`, `CO`, `EUR`, `USD`, `FP16`, `BF16`, `TFLOP`, `XI`, `AA`, `E1`, `F401`, `ID`, `ENERGY`, `PATH`, `ALLOW`, `CLONE`, `TODO`, and every two-letter country code | A unit, a symbol, a Roman numeral, a conformance level, a standard's own designation, a lint rule, part of a product name, part of an environment variable's name, or one of this package's four honesty statuses — which `STANDARDS.md` defines. |

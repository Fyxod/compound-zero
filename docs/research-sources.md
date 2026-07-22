# Research Sources and Provenance Ledger

Research date: 22 July 2026

This ledger separates organiser requirements, verified factual evidence, research datasets, and market signals. A listing here does not grant permission to redistribute source data. Dataset terms must be checked again when data is acquired and recorded in the repository's eventual data manifest.

## Source classes

- **O - Organiser primary:** official hackathon page, problem brief, or submission interface.
- **G - Government/standards primary:** government department, regulator, standards body, or official programme.
- **D - Dataset/research primary:** dataset owner, university, mission owner, or research platform.
- **M - Market signal:** vendor or project self-description; useful only for saturation analysis.
- **S - Secondary:** reputable reporting or creator self-report; clearly labelled and not treated as independent technical validation.

## Organiser sources

| ID | Class | Source | What it supports |
|---|---|---|---|
| O1 | O | Problem statement PDF: `C:\Users\parth\Downloads\6a38ce305640d_ET_AI_Hackathon_2026_Problem_Statements.pdf` | Eight official statements, deliverables, evaluation focus, and repeated 25/25/20/15/15 rubric. The 17-page PDF was text-extracted and visually checked. It is a requirements source, not a trusted factual citation source. |
| O2 | O | [ET AI Hackathon 2.0 on Unstop](https://unstop.com/competitions/crp-et-ai-hackathon-20-economic-times-1675680) | Team size, stages, eligibility, live judging categories, originality rule, licensed-tool/dataset rule, public-link rule, finale format, prizes, and participation count. Page inspected live on 22 July 2026. |
| O3 | O | Submission screenshots supplied by the participant | Mandatory detailed PDF and GitHub URL; optional additional document; three-to-four-minute video upload or external link depending on size. |
| O4 | S/O | [Official ET recap of the previous edition](https://economictimes.indiatimes.com/ai/ai-insights/et-genai-hackathon-first-edition-wraps-up-bold-ideas-win-big/articleshow/130638874.cms) | The organiser's recap says the winner stood out for technical foundation, clear problem solving, and real-world relevance. |
| O5 | S | [Previous winner's implementation self-report](https://www.linkedin.com/posts/contactsaketh_etaihackathon-grandchampion-ai-activity-7459829259511955456-SAOJ) | Self-reported use of a trained vision model, a multi-agent pipeline, multilingual output, and a pesticide safeguard. Useful as a directional signal only; implementation details were not independently audited. |

## PS1 industrial safety sources

| ID | Class | Source | Supported use or caveat |
|---|---|---|---|
| P1 | D | [Additional Tennessee Eastman Process Simulation Data for Anomaly Detection Evaluation](https://doi.org/10.7910/DVN/6C3JR1) | Publicly accessible industrial-process simulation benchmark for anomaly/fault detection. It does not include permits, worker positions, CCTV, maintenance, or real incidents. Dataset-specific licence terms must be captured before redistribution. |
| P2 | G | [OISD standards list](https://www.oisd.gov.in/en-in/oisd-standards-list) | Confirms OISD-STD-105 Work Permit System and the current-edition catalogue. The catalogue does not provide the full normative content. |
| P3 | G | [OISD purchase/access terms](https://www.oisd.gov.in/en-in/purchase-of-standards) | Current full standards are sold through authorised access. Do not bundle unofficial copies, quote unlicensed normative text, or claim full compliance coverage without authorised material. |
| P3a | G | [Occupational Safety, Health and Working Conditions Code, 2020](https://labour.gov.in/sites/default/files/osh_gazette.pdf) | Current central statutory framework used only for scoped reference navigation. Section 143 repeals the Factories Act, 1948 subject to savings; this repository is not a legal compliance assessment. |
| P3b | G | [S.O. 5321(E), Code commencement notification](https://labour.gov.in/sites/default/files/e-noti-osh-1.pdf) | Brought the Code fully into force on 21 November 2025. This corrects any treatment of the Factories Act as the current primary statute. |
| P3c | G | [Occupational Safety, Health and Working Conditions (Central) Rules, 2026](https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf) | Final G.S.R. 345(E), dated 8 May 2026 and effective on Gazette publication. Rules 23, 24 and 46 support narrowly scoped gas/ventilation and emergency-lighting navigation; they do not create a general central hot-work/PTW workflow. Applicable State/saved rules and the approved site register still require qualified review. |
| P4 | G | [DGFASLI Standard Reference Note 2024](https://dgfasli.gov.in/public/Admin/Cms/AllPdf/685e62eb37da23.32721872.pdf) | Primary factory-safety statistics. Its 2023 factory-injury table does not support the brief's attributed claim of more than 6,500 fatal workplace accidents; definitions and scope must be stated when using any number. |
| P5 | G | [Ministry of Steel release on the Visakhapatnam Steel Plant accident](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2270473&lang=1&reg=48) | Primary ministry confirmation of eight deaths and six injuries after an explosion and fireball during casting at Caster-2, Steel Melt Shop-1, on 8 June 2026. This contradicts the brief's January 2025 coke-oven narrative. |
| P6 | S | [Preliminary investigation reporting](https://indianexpress.com/article/india/vizag-steel-plant-explosion-probe-entrapped-gases-caused-blast-killed-8-workers-10730667/) | Reports a preliminary finding involving entrapped gases from liquid steel. Use conservative wording because investigation findings may evolve. |
| P7 | M | [HSSE Tech](https://hsse.tech/) | Vendor claims AI embedded in permit-to-work, inspection, and observation workflows. Used only as evidence that a generic AI/PTW concept is not novel. |

## PS5 air-quality sources

| ID | Class | Source | Supported use or caveat |
|---|---|---|---|
| A1 | G | [Real-Time Air Quality Index, Open Government Data Platform India](https://www.data.gov.in/catalog/real-time-air-quality-index) | Official CPCB/MoEFCC station data covering major pollutants. The catalog states release under NDSAP; observe the Government Open Data Licence and attribution requirements. |
| A2 | G/D | [Copernicus Sentinel-5P collection](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-5p) | Atmospheric NO2, SO2, CO, ozone, aerosol, and related products. Satellite columns are not interchangeable with ground-level exposure measurements. |
| A3 | G | [Copernicus Data Space terms](https://dataspace.copernicus.eu/terms-and-conditions) | Sentinel data is available on a free, full, and open basis under its legal notice; portal content and compute services can have separate restrictions or quotas. Preserve required credits. |
| A4 | G/D | [ERA5 hourly single-level data](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) | Hourly meteorological reanalysis from 1940 onward, updated with latency. The dataset page provides DOI and citation metadata. |
| A5 | G | [ECMWF/Copernicus CC BY 4.0 licence](https://cds.climate.copernicus.eu/licences/creative-commons-attribution-4-0-international-public-licence) | Requires formal dataset citation and attribution; changes should be indicated. |
| A6 | G | [CPCB model framework for source-apportionment studies](https://prana.cpcb.gov.in/assets/pdf/revised_SA_framework_on_esamiksha.pdf) | Supports the caveat that defensible source attribution requires inventories, measurements, source profiles, validation, QA/QC, and uncertainty treatment. |
| A7 | M/D | [PAVITRA](https://pavitra.org/) | Research initiative already offering an India-focused source-receptor and intervention-modelling platform. Used as saturation evidence, not as a validation benchmark. |
| A8 | S/G | [Delhi real-time source-apportionment and forecasting report](https://www.dpcc.delhigovt.nic.in/uploads/news/819b9fef9cf4a2a574a10d3bbc421cfd.pdf) | Evidence that forecasting, source-apportionment, and policy-action tooling is already an active government domain. |

## Sources for the remaining statements

| ID | Problem | Class | Source | Supported use or caveat |
|---|---|---|---|---|
| R1 | PS2 | G/D | [IMF and Oxford PortWatch launch](https://www.imf.org/en/news/articles/2023/11/13/pr23390-imf-university-oxford-launch-portwatch-platform-monitor-simulate-trade-disruptions) | Public maritime disruption monitoring and simulation exists. It does not supply a complete executable crude-procurement dataset. |
| R2 | PS3 | G/D | [NASA Li-ion Battery Aging Datasets](https://data.nasa.gov/dataset/li-ion-battery-aging-datasets) | Credible charge/discharge/impedance ageing data for SOH/RUL work. The portal showed “License not specified” when reviewed; confirm reuse/redistribution terms before bundling data. Lab cells are not an industrial fleet. |
| R3 | PS4 | G | [buildingSMART Information Delivery Specification](https://www.buildingsmart.org/standards/bsi-standards/information-delivery-specification-ids/) | Open, machine-readable information requirements and compliance checking for IFC models. This does not provide data-centre project records. |
| R4 | PS4 | G | [buildingSMART IFC examples](https://technical.buildingsmart.org/standards/ifc/ifc-examples/) | Sample IFC files suitable for software testing; data-centre specifications, commissioning records, RFIs, and schedules still require authorised samples. |
| R5 | PS4 | M | [Skyrn CX](https://www.skyrncx.com/) | Vendor claims an AI-powered commissioning platform for data-centre and MEP work. Saturation signal only. |
| R6 | PS6 | G | [I4C Digital Arrest advisory](https://cybercrime.gov.in/pdf/Advisories/ADVISORYTAU-ADV-003DigitalArrest06.03.2025.pdf) | Official scam pattern and citizen guidance; not a labelled audio or transaction dataset. |
| R7 | PS6 | G | [RBI banknote security features](https://rbi.org.in/scripts/PublicationsView.aspx?Id=18086) | Official descriptions of banknote security features. Ordinary RGB phone images cannot observe every physical/UV feature, so counterfeit claims require constrained scope. |
| R8 | PS6 | M | [NeoRakshak](https://neorakshak.in/) | Product self-description claiming Indian scam detection. Used only as a saturation signal. |
| R9 | PS7 | D | [MITRE ATT&CK data and tools](https://attack.mitre.org/resources/attack-data-and-tools/) | Maintained STIX/TAXII threat-knowledge data for technique mapping. ATT&CK coverage is not proof of detection coverage. |
| R10 | PS7 | G | [MITRE ATT&CK terms of use](https://attack.mitre.org/resources/terms-of-use/) | Royalty-free research/development/commercial use with required MITRE copyright and licence notice. Follow trademark guidance and do not imply endorsement. |
| R11 | PS7 | D | [CIC-IDS2017, University of New Brunswick](https://www.unb.ca/cic/datasets/ids-2017.html) | Public labelled flows/PCAPs and a clear benchmark description. It is from 2017, is not an OT/CNI dataset, and requires citation of the associated paper. Confirm redistribution terms before vendoring files. |
| R12 | PS8 | D | [DocVQA](https://www.docvqa.org/) | Public document-understanding tasks and datasets for evaluation. It is not an industrial drawing/maintenance benchmark; verify the specific challenge dataset's licence before redistribution. |

## Verified corrections

### Visakhapatnam Steel Plant

- **Brief:** January 2025, coke-oven event, eight deaths.
- **Verified minimum:** the Ministry of Steel source records eight deaths and six injuries after an explosion and fireball during casting on 8 June 2026.
- **Preliminary detail:** later reporting describes a steel-melting/ladle event and entrapped gases from liquid steel.
- **Policy:** cite P5, optionally P6 with “preliminary,” and do not use the brief's date/location narrative.

### DGFASLI fatality statistic

- **Brief:** more than 6,500 fatal workplace accidents in FY2023, attributed to DGFASLI.
- **Verification:** P4's 2023 factory table does not support that number. Other datasets may use different sector coverage, but that does not validate the attribution.
- **Policy:** omit the number unless a primary source with matching definition, sectors, and period is located.

### CBSE cyberattack narrative in PS7

- **Brief:** early-2026 pre-exam compromise of student data and emergency shutdowns across states.
- **Verified reporting:** [CBSE complaint and attack report](https://indianexpress.com/article/education/cbse-files-complaint-with-delhi-police-over-cyber-attacks-on-post-result-services-portal-10725903/) concerns June 2026 post-result services and states that CBSE reported no data breach, confidential-information compromise, or unauthorised database access.
- **Policy:** describe attempted service disruption only; do not claim a confirmed breach.

## Data and model provenance requirements

Before submission, create a machine-readable data manifest containing:

- Dataset title, owner, canonical URL/DOI, version or retrieval date, and checksum.
- Licence or terms URL, required attribution, and whether redistribution is permitted.
- Exact features used and transformations performed.
- A `real`, `public simulation`, or `project-generated simulation` classification.
- Train/validation/test split method and leakage controls.
- Known domain mismatch and limitations.

For every UI number and video claim, distinguish:

1. **Observed:** directly present in an attributed source or input stream.
2. **Estimated:** produced by a measured model with confidence/calibration.
3. **Assumed:** scenario parameter chosen for simulation.
4. **Generated:** natural-language explanation or recommendation.

This distinction is essential to preserving credibility in a safety-critical prototype.

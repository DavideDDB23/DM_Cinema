# Data Management 2025/2026 - Project Information

**Course**: Master of Science in Engineering in Computer Science / Laurea Magistrale in Ingegneria Gestionale (Sapienza - University of Rome)  
**Credits**: 6 ECTS  
**Main Instructor**: Prof. Maurizio Lenzerini  
**Project Tutor**: Roberto Maria Delfino  
**Course Period**: February - May 2026

---

## Course Overview

The Data Management course provides knowledge of:
- Structure and functionalities of relational Database Management Systems (DBMSs)
- NoSQL data models (hands-on approach)

---

## Course Schedule & Location

**Classroom**: Via delle Sette Sale 29 (SPV) - Classroom 41

**Class Times**:
- Monday: 11:15 - 13:00
- Tuesday: 14:00 - 17:00

**Course Website**: https://classroom.google.com/u/1/c/MTYyMzM4OTk1MTQx  
**Professor Website (F.A.Q.)**: https://sites.google.com/diag.uniroma1.it/rmdelfino/teaching/dm-2025-2026

---

## Exam Modalities

### Option 1: Written Exam Only
- Full standard written exam
- All problems mandatory
- Standard evaluation rules

### Option 2: Written Exam + Practical Project
- **Shortened written exam**: 15 to 24 points (minimum 15 required to pass)
- **Practical project**: 4 to 8 points (minimum 4 required to pass)
- **Final grade**: z = x + y, where z ∈ [19, 32] or 30L (honors)
- **Group size**: Individual or groups of 2 students
- **Flexibility**: Present project before or after written exam (any order)

---

## Choosing Your Exam Modality

### For Option 2 (Written Exam + Project):
1. **MUST send project proposal to** `delfino@diag.uniroma1.it` **BEFORE booking exam**
2. Wait for approval before starting work
3. Complete project and send for presentation

### For Option 1 (Written Exam Only):
- Simply book for written exam on Infostud
- No email required

**CRITICAL**: Doing the exam without communicating Option 2 choice = automatically evaluated as Option 1, without exceptions.

---

## Project Workflow

### Step 1: Project Proposal Submission

**Document**: Single-page PDF including:
- Names and student IDs (matricola) of all group members
- Chosen project type (DW, DBMS comparison, NoSQL tool, etc.)
- Description of dataset(s) with reference link
- Brief description (5-10 lines) of intended work

**Email Requirements**:
- **Subject**: `[DM] Project Proposal`
- **Attachment**: PDF document (single page)
- **CC**: All group members must be included (sender or CC)
- **Send to**: `delfino@diag.uniroma1.it`

**Important**: Do NOT start working before receiving approval feedback.

### Step 2: Project Development

- Start working only after proposal is accepted
- You may ask for help if struggling with specific parts
- Focus on content, not fancy tools

### Step 3: Project Presentation

**Email Requirements**:
- **Subject**: `[DM] Project Discussion`
- **Attachment**: Your slides (PowerPoint, PDF, etc.)
- **Include**: Links to additional material (GitHub repo, datasets, etc.) - provide links, no zip files
- **Specify**: Remote or in-person presentation preference
- **Send to**: `delfino@diag.uniroma1.it`

**Presentation Format**:
- 10 to 15 minutes slideshow presentation (MUST stick to time limit)
- 5 minutes live demo
- Questions may be asked to verify eligibility for honors grade

**Response**: Prof. Delfino will either:
- Propose appointment to present project, OR
- Suggest possible improvements

---

## Project Evaluation Criteria

### Scoring
- **Project score range**: 0 to 8 points
- **Written exam score range**: 0 to 24 points
- **Final grade**: Project points + Written exam points (19-32 or 30L)

### Pass Requirements
- Minimum 4 points on project (if Option 2)
- Minimum 15 points on written exam (if Option 2)
- Both must pass for exam registration

### Project Completion
- If project requirements fulfilled → marked as **passed**
- Marks depend on complexity and quality of execution

---

## Deadlines (CRITICAL)

| Item | Deadline |
|------|----------|
| **Project Proposal Submission** | August 31, 2026 |
| **Project Presentation** | September 30, 2026 |
| **Option 2 Validity** | September 30, 2026 |

**PENALTY FOR MISSED DEADLINE**:
- Miss September 30 deadline = project considered void
- Student must take exam according to Option 1
- If already took shortened exam (Option 2): must answer one additional question on written exam

---

## Project Ideas & Focus Areas

### Data Warehousing (DW) Projects

#### Idea 1: Multi-Source ETL + Star/Snowflake Schema + OLAP
- Select set of data sources
- Integrate via ETL operations (tool or simple scripts)
- Define DFM model
- Define and populate Star or Snowflake schema (relational DB e.g., Postgres)
- Perform OLAP queries
- **Focus**: Ability to combine data from different datasets for unified analysis source

#### Idea 2: Technology Comparison
- Identify data analysis problem
- Compare different approaches (e.g., relational DBMS vs. DW tool)
- **Focus**: Ability to compare different technologies

#### Idea 3: Dataset Analysis + Report
- Select dataset from domain of interest
- Carry out relevant analyses
- Produce report showing results
- **Focus**: Ability to identify interesting phenomena (not explicit in data) and show how technology communicates findings

### NoSQL Projects

#### Idea 4: Graph Database vs. Relational Comparison
- Select dataset
- Choose graph database tool
- Use relational DBMS
- Compare results on different systems
- Highlight advantages/disadvantages regarding efficiency
- **Focus**: Ability to compare different technologies

#### Idea 5: Graph Database Learning Project
- Select graph database tool
- Acquire reasonable knowledge on it
- Develop simple database project using tool
- **Focus**: Ability to acquire new tool knowledge and apply in real case scenario

---

## Requirements for Maximum Grade (8 Points)

### General Requirements
- Demonstrate reasonable level of complexity
- Provide non-trivial and accurate modeling
- Include detailed and well-motivated analyses
- Questions may be posed to establish honors grade eligibility

### Data Warehousing - Specific Requirements

**Mandatory**:
- DFM (Dimensional Fact Model) schema
- Star OR Snowflake schema (must justify choice)

**For High Grade**:
- Choose dataset carefully (suitable for analysis)
- Make DFM schema sketch BEFORE proposal submission
- Minimum 3 non-trivial dimensions with hierarchies for OLAP
- Show interesting insights via OLAP sessions
- Provide SQL queries for Star/Snowflake schema
- Design and implement Reconciled Layer using ETL operations (contributes to higher evaluation)

### NoSQL / Relational Comparison - Specific Requirements

**For High Grade**:
- Choose dataset carefully
- Avoid too small datasets (unsuitable for highlighting system peculiarities)
- Carefully design conceptual modeling for both relational and NoSQL cases
- Justify modeling choices
- Avoid trivial modeling (e.g., single edge type, single node type)
- Compare on multiple aspects:
  - Performance on specific queries
  - Query language complexity
  - Ease-of-use
  - Scalability
  - Efficiency of different approaches

---

## Data Sources & Integration

### Dataset Selection Guidelines
- Do NOT blindly import CSVs as-is (they usually aren't organized per relational model)
- Understand data semantics
- Design proper conceptual model
- Free to exclude irrelevant data
- Encouraged to integrate different sources into unified database view

### Where to Find Datasets

- kaggle.com/datasets
- data.europa.eu
- opendata.cern.ch
- earthdata.nasa.gov
- dati.gov.it (Italian only)
- data.gov
- datasetsearch.research.google.com

---

## Common Questions & Answers (F.A.Q.)

### Project Organization & Presentation

**Q1: Are there specific dates for project presentations?**  
A: No. As soon as you complete your project, request appointment following indications in slides.

**Q2: Can project presentations be done only in person?**  
A: No. Remote presentations allowed via Google Meet (ask for link).

**Q3: I want maximum grade. Can I request ongoing feedback to adjust work?**  
A: No. Evaluations not provided before presentation (time-consuming + evaluation should reflect your work, not professor's). General advice on content coverage available.

**Q4: Is well-done project always worth 8 points?**  
A: Not necessarily. Propose simpler project if not aiming for highest score but prefer shorter time. Propose complex project if aiming for maximum. Ask if unsure about complexity vs. expectations.

**Q5: I'm facing problems/unsure how to proceed. Can I ask for help?**  
A: Yes. Reach out whenever struggling. Prof will provide suggestions to overcome obstacles.

**Q6: My project includes code. How to share it?**  
A: Provide link to repository. Do NOT send zip files.

### Exam Registration & Deadlines

**Q7: What's last date for presenting project to have grade registered in specific exam session?**  
A: Unknown. Check with administration.

**Q8: Already passed written test but not project presentation. Must I re-book written exam?**  
A: Yes. If about to complete project for upcoming exam session, book for that session and inform Prof. Lenzerini you booked for registration only. If presenting outside exam session, book first useful exam session.

### Project Grading & Re-submission

**Q9: Not satisfied with project grade. Can I change and re-present?**  
A: No. Refuse grade = required to do new project.

**Q10: What requirements for maximum project grade?**  
A: Reasonable complexity, non-trivial modeling, detailed well-motivated analyses. Questions may be posed to verify honors grade eligibility.

### Data Warehousing Specific (High Grade)

**Q11: Doing DW project. What aspects matter for high grade?**  
A: 
- Choose dataset carefully
- Sketch DFM schema before proposal
- Minimum 3 non-trivial dimensions (with hierarchies for OLAP)
- Show interesting OLAP insights
- Provide SQL queries for Star/Snowflake (justify schema choice)
- Design & implement Reconciled Layer (ETL) contributes to higher evaluation
- **DFM + Star/Snowflake schema MANDATORY for every DW project**

### NoSQL/Relational Comparison Specific (High Grade)

**Q12: Comparing relational & graph models. What aspects for high grade?**  
A: 
- Choose dataset carefully
- Avoid too small datasets
- Design conceptual modeling for both approaches, justify choices
- Avoid trivial modeling (single edge/node type)
- Compare different aspects: performance on specific queries, query language complexity, ease-of-use, scalability

### Data Import & ETL

**Q13: Found dataset (CSVs). Import as-is into database?**  
A: No. Many online datasets aren't organized per relational model. Understand semantics, design proper conceptual model. Free to exclude irrelevant data and integrate different sources into unified view.

### Tool Limitations

**Q14: My tool can't connect to relational DB (e.g., Tableau Public). What to do?**  
A: Still design and implement relational reconciled layer. Instead of executing SQL ETL, formulate queries. Convert relational DB to tool-compatible format. Actual import may differ from SQL approach. Shows what would be done in ROLAP system.

### Project Deadlines

**Q15: Deadline for presenting proposals and having project discussions?**  
A: 
- **New project proposals**: August 31, 2026 deadline
- **Project presentations**: September 30, 2026 deadline
- Students not presenting proposal by August 31 and not presenting project by September 30 automatically set to Option 1. May need to integrate written exam grade.

---

## Office Hours & Contact

**Email**: `delfino@diag.uniroma1.it`

**In-Person Office Hours**:
- Location: Room B213, second floor
- Department of Computer, Control and Management Engineering
- Via Ariosto 25, 00185, Rome

**Remote Office Hours**:
- Google Meet: meet.google.com/zic-bxwa-cia

**How to Schedule**:
- Send email briefly describing what you want to discuss
- Office hours available both in-person and remotely

---

## Important Tips & Advice

### General
- Challenge yourselves, but don't underestimate workload
- In group projects: don't let partner do all work, and don't do all work yourself → cooperate!
- Focus on content, not fancy tools (professor won't buy anything special)
- Use as opportunity to improve writing and communication skills

### Before Asking Questions
To avoid upsetting the professor, check these resources first:
- Website of the course
- Professor's F.A.Q. website
- Project instruction slides

---

## Summary Checklist

- [ ] Decide: Option 1 (written only) or Option 2 (written + project)
- [ ] If Option 2: Email proposal to `delfino@diag.uniroma1.it` BEFORE booking exam (deadline: August 31)
- [ ] Wait for proposal approval
- [ ] Develop project
- [ ] Prepare 10-15 min slides + 5 min demo
- [ ] Email completed project with links (deadline: September 30)
- [ ] Present project (remote or in-person)
- [ ] Pass both parts (project ≥4, written ≥15) for registration

---

**Last Updated**: July 2026  
**Source**: DM2526 Instructions on projects (PDF) + Course website

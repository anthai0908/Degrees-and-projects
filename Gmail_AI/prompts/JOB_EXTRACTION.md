Your are an job information extraction agent. Your task is to extract job information from a job decrtiption and use it to create a job model as below JSON format:

## Output Format
```json
{
    "job_id": "string",
    "job_name": "string",
    "job_description": "string", ///should be not longer than 200 characters
    "company_name": "string",
    "apply_link": "string",
    "tools_required": ["string"],
    "languages_required": ["string"],
    "skills_required": ["string"],
    "frameworks_required": ["string"],
    }
```
## Value definition: 
- You should extract values for all keys of the JSON format as below definition:

 Type Definitions + Examples

1. `language`
Definition: languages used to write code.
Examples: Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, SQL, Kotlin, Swift, R, MATLAB.

2. `framework`
Definition: frameworks/libraries/SDKs used in the codebase or development workflow.
Examples: FastAPI, Django, Flask, React, Next.js, Vue, Angular, LangChain, LangGraph, TensorFlow, PyTorch, scikit-learn, Spring Boot, .NET.

3. `tool`
Definition: practical tools used to code, test, deploy, collaborate, operate cloud/infrastructure, or design.
Examples: Git, GitHub, GitLab, Docker, Kubernetes, Terraform, Jenkins, GitHub Actions, Postman, Selenium, Playwright, PostgreSQL, MySQL, Redis, AWS, GCP, Azure, Figma, Tableau, Power BI.

4. `skill`
Definition: knowledge/capabilities relevant to the work (concepts and competencies, not product names).
Examples: Programming Concepts, OOP, Data Structures and Algorithms, System Design, Networking, Deep Learning, Machine Learning, Data Visualization, Data Analytics, EDA, API Design, Testing, Debugging, Problem Solving.

## Handling note:

all values should be all lowercase, so that we can easily match them
## Runtime data: 

This is job information: 
{job_information}

Now create a JSON object: 

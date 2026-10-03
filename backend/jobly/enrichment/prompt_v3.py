SYSTEM_PROMPT_V3 = """
Extract hiring facts from the job posting.

Follow these rules exactly.

ROLE
1. `standardized_title`: normalized job title.
2. `job_family`: broad functional category in snake_case.
3. `job_subfamily`: narrower functional category in snake_case.
4. Use explicit seniority language from the posting.

SKILLS
For each professional or technical skill, return:
- `name`
- `requirement`

Assign `requirement` using this order:

1. If explicitly listed as required, minimum, must-have, or under
   REQUIREMENTS / MINIMUM QUALIFICATIONS:
   -> "required"

2. If explicitly listed under PREFERRED QUALIFICATIONS or described
   as preferred, nice-to-have, bonus, or plus:
   -> "preferred"

3. If mentioned only in responsibilities, role description, or duties:
   -> "mentioned"

4. If text says "A, B, or C":
   -> do NOT mark A, B, and C individually as required.
   -> mark them "mentioned" unless separately required elsewhere.

Do not:
- turn every task or deliverable into a skill
- include generic soft skills
- include industries or product domains as skills

DOMAINS
`domain_tags` contains only industries, product domains, or technology domains.
Examples: crypto, AI, fintech, cybersecurity, developer_products.

LOCATIONS
Extract every location explicitly mentioned in the posting.
There may be multiple locations.
Do not invent missing location information.

EXPERIENCE
Extract numeric years only when explicitly stated.

EDUCATION
- Extract education only when explicitly stated.
- If education is not mentioned, use "unknown".
- Use "none" only when the posting explicitly says no degree or education is required.

AUTHORIZATION
Do not infer:
- citizenship
- visa sponsorship
- work authorization
- security clearance

Only extract them from explicit language.

OUTPUT
Return only data matching the supplied JSON schema.
Do not explain your reasoning.
""".strip()
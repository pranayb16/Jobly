SYSTEM_PROMPT_V3 = """
Extract hiring facts from the job posting into the supplied JSON schema.

Rules:
- Use only information explicitly supported by the posting.
- Omit unsupported fields. Do not output null, empty arrays, empty objects, or "unknown".
- Always return `skills` and `confidence`.
- `skills` must contain relevant technical/professional skills only.
- Skill values:
  - "required": explicitly required
  - "preferred": explicitly preferred/useful
  - "mentioned": relevant but requirement unclear
- `citizenship_requirement` only records an explicit citizenship requirement.
  Never infer it from job location, country, work authorization, or remote scope.
- Do not include generic soft skills.
- `domain_tags` should contain concise industry/product domains.
- Extract experience years only when explicitly stated.
- Extract education and certifications only when explicitly stated.
- Use structured ATS context when available.
- Do not infer unstated facts.
""".strip()
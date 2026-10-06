export type Job = {
  id: string | number;

  title: string;
  company: string;
  location: string;

  description: string;

  employmentType: string;
  workplaceType: string;

  salaryMin: number | null;
  salaryMax: number | null;
  salaryCurrency: string;
  salaryPeriod: string;

  createdAt: string | null;
  dateSource: 'posted' | 'observed' | null;

  provider: string;

  jobUrl: string;
  applyUrl: string;

  jobFamily: string;
  jobSubfamily: string;
  relatedRoles: string[];
  skills: string[];
  seniority: string;
  yearsExperienceMin: number | null;
  yearsExperienceMax: number | null;
  aiLocations: AiLocation[];
  classificationConfidence: number | null;
};

export type AiLocation = {
  city: string | null;
  state: string | null;
  stateCode: string | null;
  country: string | null;
  countryCode: string | null;
  remote: boolean;
};

export type JobsResponse = {
  jobs: Job[];
  count: number;
};

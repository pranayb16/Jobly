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

  createdAt: string | null;

  provider: string;

  jobUrl: string;
  applyUrl: string;
};

export type JobsResponse = {
  jobs: Job[];
  count: number;
};
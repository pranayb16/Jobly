export const FILTER_GROUP_ORDER = [
  'datePosted',
  'location',
  'workplace',
  'role',
  'experience',
  'employment',
  'skill',
  'company',
  'source',
] as const;

export type FilterKey = (typeof FILTER_GROUP_ORDER)[number];

export type Filters = Record<FilterKey, string[]>;

export type FilterOption = {
  value: string;
  label: string;
  count?: number;
};

export type FilterDefinition = {
  key: FilterKey;
  label: string;
  options: FilterOption[];
  searchable?: boolean;
  single?: boolean;
};

export type ActiveFilterGroup = {
  key: FilterKey | 'saved';
  label: string;
  values: FilterOption[];
};

export type Sort = 'newest' | 'oldest' | 'company';

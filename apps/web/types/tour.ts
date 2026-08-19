export type Continent = "iran" | "asia" | "europe" | "africa" | "south-america";
export type TripType = "domestic" | "international";
export type Budget = "low" | "mid" | "high";

export type Tour = {
  id: string;
  city: string;
  cityLabel: string;
  region: string;
  kind: TripType;
  title: string;
  meta: string;
  hotel: string;
  price: number | null;
  services: string;
  tag: string;
  continent: Continent;
};

export type TourFilters = {
  continent?: Continent;
  tripType?: TripType;
  budget?: Budget;
};

export type TourListResponse = {
  items: Tour[];
  count: number;
};

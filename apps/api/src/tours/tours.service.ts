import { BadRequestException, Injectable, NotFoundException } from "@nestjs/common";
import { TOURS } from "./tours.data";

type Filters = {
  continent?: string;
  tripType?: string;
  budget?: string;
};

export type ManagedTour = {
  id: string;
  city: string;
  cityLabel: string;
  region: string;
  kind: string;
  title: string;
  meta: string;
  hotel: string;
  price: number | null;
  services: string;
  tag: string;
  continent: string;
  active: boolean;
};

@Injectable()
export class ToursService {
  private readonly tours: ManagedTour[] = TOURS.map((tour) => ({ ...tour, active: true })) as ManagedTour[];

  findAll(filters: Filters) {
    const items = this.tours.filter((tour) => {
      if (!tour.active) return false;
      if (filters.continent && tour.continent !== filters.continent) return false;
      if (filters.tripType && tour.kind !== filters.tripType) return false;

      if (filters.budget) {
        if (tour.price === null) return false;
        if (filters.budget === "low" && tour.price > 30_000_000) return false;
        if (filters.budget === "mid" && (tour.price <= 30_000_000 || tour.price > 70_000_000)) return false;
        if (filters.budget === "high" && tour.price <= 70_000_000) return false;
      }

      return true;
    });

    return { items, count: items.length };
  }

  findOne(id: string) {
    const tour = this.tours.find((item) => item.id === id && item.active);
    if (!tour) throw new NotFoundException("Tour not found");
    return tour;
  }

  findManaged() {
    return [...this.tours];
  }

  updateManaged(id: string, input: { price?: number | null; active?: boolean; tag?: string }) {
    const tour = this.tours.find((item) => item.id === id);
    if (!tour) throw new NotFoundException("Tour not found");

    if (input.price !== undefined) {
      if (input.price !== null && (!Number.isFinite(input.price) || input.price < 0)) {
        throw new BadRequestException("Invalid price");
      }
      tour.price = input.price;
    }

    if (typeof input.active === "boolean") tour.active = input.active;
    if (typeof input.tag === "string" && input.tag.trim()) tour.tag = input.tag.trim().slice(0, 40);

    return tour;
  }
}

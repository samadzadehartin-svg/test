import { Injectable } from '@nestjs/common';

@Injectable()
export class ToursService {
  private readonly tours = [
    { id: 1, title: 'دبی', country: 'امارات', nights: 4, days: 5, price: 22900000, oldPrice: 32900000, discount: 30, image: 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1000&q=80' },
    { id: 2, title: 'استانبول', country: 'ترکیه', nights: 5, days: 6, price: 14200000, oldPrice: 18700000, discount: 24, image: 'https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=1000&q=80' },
    { id: 3, title: 'پوکت', country: 'تایلند', nights: 6, days: 7, price: 39900000, oldPrice: 50900000, discount: 21, image: 'https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?auto=format&fit=crop&w=1000&q=80' },
    { id: 4, title: 'باکو', country: 'آذربایجان', nights: 3, days: 4, price: 14900000, oldPrice: 19900000, discount: 25, image: 'https://images.unsplash.com/photo-1558862107-d49ef2a04d72?auto=format&fit=crop&w=1000&q=80' },
  ];

  findAll(destination?: string) {
    if (!destination) return this.tours;
    const query = destination.trim().toLowerCase();
    return this.tours.filter((tour) => `${tour.title} ${tour.country}`.toLowerCase().includes(query));
  }
}

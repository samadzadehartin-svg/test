export type Destination = {
  id: number;
  name: string;
  country: string;
  image: string;
};

export type Tour = {
  id: number;
  title: string;
  country: string;
  nights: number;
  days: number;
  price: number;
  oldPrice?: number;
  discount?: number;
  image: string;
};

export const fallbackDestinations: Destination[] = [
  { id: 1, name: "استانبول", country: "ترکیه", image: "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=900&q=80" },
  { id: 2, name: "وان", country: "ترکیه", image: "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=900&q=80" },
  { id: 3, name: "تایلند", country: "تایلند", image: "https://images.unsplash.com/photo-1508009603885-50cf7c579365?auto=format&fit=crop&w=900&q=80" },
  { id: 4, name: "ارمنستان", country: "ارمنستان", image: "https://images.unsplash.com/photo-1605470207062-b72b5cbe2a87?auto=format&fit=crop&w=900&q=80" },
  { id: 5, name: "گرجستان", country: "گرجستان", image: "https://images.unsplash.com/photo-1565008576549-57569a49371d?auto=format&fit=crop&w=900&q=80" },
  { id: 6, name: "دبی", country: "امارات", image: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=900&q=80" },
  { id: 7, name: "روسیه", country: "روسیه", image: "https://images.unsplash.com/photo-1513326738677-b964603b136d?auto=format&fit=crop&w=900&q=80" }
];

export const fallbackTours: Tour[] = [
  { id: 1, title: "دبی", country: "امارات", nights: 4, days: 5, price: 22900000, oldPrice: 32900000, discount: 30, image: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1000&q=80" },
  { id: 2, title: "استانبول", country: "ترکیه", nights: 5, days: 6, price: 14200000, oldPrice: 18700000, discount: 24, image: "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=1000&q=80" },
  { id: 3, title: "پوکت", country: "تایلند", nights: 6, days: 7, price: 39900000, oldPrice: 50900000, discount: 21, image: "https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?auto=format&fit=crop&w=1000&q=80" },
  { id: 4, title: "باکو", country: "آذربایجان", nights: 3, days: 4, price: 14900000, oldPrice: 19900000, discount: 25, image: "https://images.unsplash.com/photo-1558862107-d49ef2a04d72?auto=format&fit=crop&w=1000&q=80" }
];

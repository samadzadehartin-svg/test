import { Injectable } from '@nestjs/common';

@Injectable()
export class DestinationsService {
  private readonly destinations = [
    { id: 1, name: 'استانبول', country: 'ترکیه', image: 'https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=900&q=80' },
    { id: 2, name: 'وان', country: 'ترکیه', image: 'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=900&q=80' },
    { id: 3, name: 'تایلند', country: 'تایلند', image: 'https://images.unsplash.com/photo-1508009603885-50cf7c579365?auto=format&fit=crop&w=900&q=80' },
    { id: 4, name: 'ارمنستان', country: 'ارمنستان', image: 'https://images.unsplash.com/photo-1605470207062-b72b5cbe2a87?auto=format&fit=crop&w=900&q=80' },
    { id: 5, name: 'گرجستان', country: 'گرجستان', image: 'https://images.unsplash.com/photo-1565008576549-57569a49371d?auto=format&fit=crop&w=900&q=80' },
    { id: 6, name: 'دبی', country: 'امارات', image: 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=900&q=80' },
    { id: 7, name: 'روسیه', country: 'روسیه', image: 'https://images.unsplash.com/photo-1513326738677-b964603b136d?auto=format&fit=crop&w=900&q=80' },
  ];

  findAll() { return this.destinations; }
}

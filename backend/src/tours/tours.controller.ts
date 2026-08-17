import { Controller, Get, Query } from '@nestjs/common';
import { ToursService } from './tours.service';

@Controller('tours')
export class ToursController {
  constructor(private readonly toursService: ToursService) {}

  @Get()
  findAll(@Query('destination') destination?: string) {
    return this.toursService.findAll(destination);
  }
}

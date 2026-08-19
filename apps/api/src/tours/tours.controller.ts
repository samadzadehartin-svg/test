import { Controller, Get, Param, Query } from "@nestjs/common";
import { ToursService } from "./tours.service";

@Controller("tours")
export class ToursController {
  constructor(private readonly toursService: ToursService) {}

  @Get()
  findAll(
    @Query("continent") continent?: string,
    @Query("tripType") tripType?: string,
    @Query("budget") budget?: string,
  ) {
    return this.toursService.findAll({ continent, tripType, budget });
  }

  @Get(":id")
  findOne(@Param("id") id: string) {
    return this.toursService.findOne(id);
  }
}

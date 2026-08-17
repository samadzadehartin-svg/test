import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { ToursModule } from './tours/tours.module';
import { DestinationsModule } from './destinations/destinations.module';

@Module({
  imports: [ToursModule, DestinationsModule],
  controllers: [AppController],
})
export class AppModule {}

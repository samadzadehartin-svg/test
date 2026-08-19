import { Module } from "@nestjs/common";
import { AuthModule } from "./auth/auth.module";
import { HealthController } from "./health.controller";
import { LeadsModule } from "./leads/leads.module";
import { StaffModule } from "./staff/staff.module";
import { ToursModule } from "./tours/tours.module";

@Module({
  imports: [AuthModule, ToursModule, LeadsModule, StaffModule],
  controllers: [HealthController],
})
export class AppModule {}

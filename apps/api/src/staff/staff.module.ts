import { Module } from "@nestjs/common";
import { AuthModule } from "../auth/auth.module";
import { LeadsModule } from "../leads/leads.module";
import { ToursModule } from "../tours/tours.module";
import { StaffController } from "./staff.controller";
import { StaffService } from "./staff.service";

@Module({
  imports: [AuthModule, LeadsModule, ToursModule],
  controllers: [StaffController],
  providers: [StaffService],
})
export class StaffModule {}

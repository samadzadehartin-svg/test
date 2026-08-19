import { SetMetadata } from "@nestjs/common";
import type { StaffRole } from "./auth.types";

export const ROLES_KEY = "staff_roles";
export const Roles = (...roles: StaffRole[]) => SetMetadata(ROLES_KEY, roles);

import { Injectable, UnauthorizedException } from "@nestjs/common";
import { randomBytes, timingSafeEqual } from "node:crypto";
import type { StaffRole, StaffSession, StaffUser } from "./auth.types";

@Injectable()
export class AuthService {
  private readonly sessions = new Map<string, StaffSession>();

  private readonly users: Array<StaffUser & { password: string }> = [
    {
      id: "admin-1",
      name: "مدیر سیستم",
      username: process.env.ADMIN_USERNAME ?? "admin",
      password: process.env.ADMIN_PASSWORD ?? "admin123",
      role: "admin",
    },
    {
      id: "expert-1",
      name: "کارشناس فروش",
      username: process.env.EXPERT_USERNAME ?? "expert",
      password: process.env.EXPERT_PASSWORD ?? "expert123",
      role: "expert",
    },
  ];

  login(username?: string, password?: string) {
    const normalizedUsername = username?.trim();
    if (!normalizedUsername || !password) {
      throw new UnauthorizedException("نام کاربری یا رمز عبور نادرست است");
    }

    const user = this.users.find((item) => item.username === normalizedUsername);
    if (!user || !this.safeEqual(user.password, password)) {
      throw new UnauthorizedException("نام کاربری یا رمز عبور نادرست است");
    }

    const token = randomBytes(32).toString("hex");
    const expiresAt = Date.now() + 8 * 60 * 60 * 1000;
    const session: StaffSession = {
      id: user.id,
      name: user.name,
      username: user.username,
      role: user.role,
      token,
      expiresAt,
    };

    this.sessions.set(token, session);

    return {
      token,
      expiresAt,
      user: this.toPublicUser(session),
    };
  }

  logout(token?: string) {
    if (token) this.sessions.delete(token);
    return { ok: true };
  }

  getSession(token?: string): StaffSession | null {
    if (!token) return null;
    const session = this.sessions.get(token);
    if (!session) return null;
    if (session.expiresAt <= Date.now()) {
      this.sessions.delete(token);
      return null;
    }
    return session;
  }

  requireSession(token?: string) {
    const session = this.getSession(token);
    if (!session) throw new UnauthorizedException("نشست کاربری معتبر نیست");
    return session;
  }

  hasRole(user: StaffUser, roles: StaffRole[]) {
    return roles.includes(user.role);
  }

  private toPublicUser(session: StaffSession): StaffUser {
    return {
      id: session.id,
      name: session.name,
      username: session.username,
      role: session.role,
    };
  }

  private safeEqual(expected: string, actual: string) {
    const a = Buffer.from(expected);
    const b = Buffer.from(actual);
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  }
}

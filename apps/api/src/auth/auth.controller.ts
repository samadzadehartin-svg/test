import { Body, Controller, Get, Headers, Post } from "@nestjs/common";
import { AuthService } from "./auth.service";

@Controller("auth")
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Post("login")
  login(@Body() body: { username?: string; password?: string }) {
    return this.authService.login(body.username, body.password);
  }

  @Get("me")
  me(@Headers("authorization") authorization?: string) {
    const session = this.authService.requireSession(this.extractToken(authorization));
    return {
      id: session.id,
      name: session.name,
      username: session.username,
      role: session.role,
    };
  }

  @Post("logout")
  logout(@Headers("authorization") authorization?: string) {
    return this.authService.logout(this.extractToken(authorization));
  }

  private extractToken(authorization?: string) {
    return authorization?.startsWith("Bearer ") ? authorization.slice(7) : undefined;
  }
}

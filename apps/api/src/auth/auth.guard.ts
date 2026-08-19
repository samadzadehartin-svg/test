import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from "@nestjs/common";
import { AuthService } from "./auth.service";

@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private readonly authService: AuthService) {}

  canActivate(context: ExecutionContext) {
    const request = context.switchToHttp().getRequest();
    const authorization = request.headers.authorization as string | undefined;
    const token = authorization?.startsWith("Bearer ") ? authorization.slice(7) : undefined;
    const session = this.authService.getSession(token);
    if (!session) throw new UnauthorizedException("Unauthorized");
    request.staffUser = {
      id: session.id,
      name: session.name,
      username: session.username,
      role: session.role,
    };
    return true;
  }
}

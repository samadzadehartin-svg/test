import { NestFactory } from "@nestjs/core";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { cors: false });

  app.setGlobalPrefix("api");
  app.enableCors({
    origin: process.env.FRONTEND_ORIGIN ?? "http://localhost:3000",
    methods: ["GET", "POST"],
  });

  const port = Number(process.env.PORT ?? 4000);
  await app.listen(port);
  console.log(`Safaro API: http://localhost:${port}/api`);
}

bootstrap();

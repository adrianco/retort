import { Router, Request, Response } from 'express';

export class HealthController {
  private router: Router;

  constructor() {
    this.router = Router();
    this.setupRoutes();
  }

  private setupRoutes(): void {
    this.router.get('/', this.healthCheck.bind(this));
  }

  public getRouter(): Router {
    return this.router;
  }

  private healthCheck(req: Request, res: Response): void {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
  }
}

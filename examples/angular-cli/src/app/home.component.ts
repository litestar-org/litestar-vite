import { Component, OnInit, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { CommonModule } from "@angular/common";

interface ApiResponse {
  message: string;
}

interface DataResponse {
  items: { id: number; name: string }[];
  total: number;
}

@Component({
  selector: "app-home",
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <h2>Welcome to Angular CLI + Litestar</h2>
      <p>
        This example demonstrates Angular 18+ with Angular CLI and a Litestar
        backend.
      </p>
    </div>

    <div class="card">
      <h3>API Response</h3>
      <p *ngIf="message">{{ message }}</p>
      <p *ngIf="!message">Loading...</p>
    </div>

    <div class="card">
      <h3>Data from API</h3>
      <ul *ngIf="items.length > 0">
        <li *ngFor="let item of items">{{ item.name }} (ID: {{ item.id }})</li>
      </ul>
      <p *ngIf="items.length === 0">Loading data...</p>
    </div>
  `,
  styles: [
    `
      h2 {
        color: #d32f2f;
        margin-bottom: 0.5rem;
      }
      h3 {
        color: #666;
        margin-bottom: 0.5rem;
      }
      ul {
        list-style: none;
        padding: 0;
      }
      li {
        padding: 0.5rem;
        background: #f5f5f5;
        margin-bottom: 0.25rem;
        border-radius: 4px;
      }
    `,
  ],
})
export class HomeComponent implements OnInit {
  private http = inject(HttpClient);

  message = "";
  items: { id: number; name: string }[] = [];

  ngOnInit() {
    // Fetch greeting from API
    this.http.get<ApiResponse>("/api/hello").subscribe({
      next: (response) => {
        this.message = response.message;
      },
      error: (error) => {
        this.message = "Error fetching message: " + error.message;
      },
    });

    // Fetch data from API
    this.http.get<DataResponse>("/api/data").subscribe({
      next: (response) => {
        this.items = response.items;
      },
      error: (error) => {
        console.error("Error fetching data:", error);
      },
    });
  }
}

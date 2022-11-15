import { Component, OnInit } from '@angular/core';
import { FilterComponent } from "@app/shared/configuration/tools/filter/filter.component";

@Component({
  selector: 'app-server-filter',
  templateUrl: '../filter/filter.component.html',
  styleUrls: ['../filter/filter.component.scss']
})
export class ServerFilterComponent extends FilterComponent implements OnInit {

  constructor() {
    super();
  }

  ngOnInit(): void {
  }

}

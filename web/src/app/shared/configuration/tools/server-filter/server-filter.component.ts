import { Component, Input, OnInit } from '@angular/core';
import { FilterComponent, IFilter } from "@app/shared/configuration/tools/filter/filter.component";

@Component({
  selector: 'app-server-filter',
  templateUrl: '../filter/filter.component.html',
  styleUrls: ['../filter/filter.component.scss']
})
export class ServerFilterComponent extends FilterComponent implements OnInit {
  constructor() {
    super();
  }

  ngOnInit() {
    this.availableFilters = this.filterList.map((filter: IFilter) => ({
      id: filter.id,
      name: filter.name,
      display_name: filter.display_name,
      filter_field: filter.filter_field,
      filter_type: filter.filter_type
    }));

    this.availableFilters.forEach((i: IFilter) => {
      this.filtersByType[i.filter_field] = i.filter_type;
    })
  }

  applyFilters() {
    const filters = this.filterForm.value;

    if (Object.keys(filters).filter((f) => {
      if (filters[f] === '' || filters[f] === undefined) {
        delete filters[f];
        return false;
      } else return true;
    }).length === 0) {
      return;
    }
  }

}

import { Component, Input, OnInit } from '@angular/core';
import { FilterComponent, IFilter } from "@app/shared/configuration/tools/filter/filter.component";
import { BehaviorSubject } from "rxjs";
import { FormControl, FormGroup } from "@angular/forms";

@Component({
  selector: 'app-server-filter',
  templateUrl: '../filter/filter.component.html',
  styleUrls: ['../filter/filter.component.scss']
})
export class ServerFilterComponent extends FilterComponent implements OnInit {
  @Input() filterParams$: BehaviorSubject<any>;
  @Input() entity: string;

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

    let listParam = localStorage.getItem('list:param');

    if (listParam) {
      const json = JSON.parse(listParam);
      Object.keys(json[this.entity]).forEach((name) => {
        this.toggleFilters(this.availableFilters.find((f) => f.name === name));
        this.filterForm.get(name).setValue(json[this.entity][name]);
      });
      this.applyFilters();
    }
  }

  applyFilters(): void {
    const filters = this.filterForm.value;

    if (Object.keys(filters).filter((f) => {
      if (filters[f] === '' || filters[f] === undefined) {
        delete filters[f];
        return false;
      } else return true;
    }).length === 0) {
      this.filterParams$.next({});
      return;
    }

    this.filterParams$.next(filters);
  }

  toggleFilters(filter): void {
    if (this.activeFilters.includes(filter.id)) {
      this.activeFilters = this.activeFilters.filter((f) => f !== filter.id);
      this.localStorageManaging(filter);
      this.filterForm.removeControl(filter.filter_field);
    } else {
      this.activeFilters.push(filter.id);
      if (filter.filter_type === 'datepicker') {
        this.filterForm.addControl(filter.filter_field, new FormGroup({
          start: new FormControl(new Date()),
          end: new FormControl(new Date()),
        }));
      } else this.filterForm.addControl(filter.filter_field, new FormControl(''))
    }
  }

  localStorageManaging(filter): void {
    const listParamStr = localStorage.getItem('list:param');

    if (listParamStr) {
      const json = JSON.parse(listParamStr);
      delete json[this.entity][filter.filter_field];

      if (Object.keys(json[this.entity]).length === 0) {
        delete json[this.entity];
      }

      if (Object.keys(json).length === 0) {
        localStorage.removeItem('list:param');
      } else localStorage.setItem('list:param', JSON.stringify(json));
    }
  }

}

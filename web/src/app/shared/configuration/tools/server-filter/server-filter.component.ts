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

  filterArr: string[];

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

    this.filterArr = this.filterList.map((filter: IFilter) => (filter.name));

    this.availableFilters.forEach((i: IFilter) => {
      this.filtersByType[i.filter_field] = i.filter_type;
    })

    const listParam = localStorage.getItem('list:param');

    if (listParam) {
      const json = JSON.parse(listParam);

      if (json[this.entity]) {
        this.manageDatepickerValue(json);
        Object.keys(json[this.entity]).forEach((name) => {
          if (!this.filterArr.includes(name)) return;

          this.toggleFilters(this.availableFilters.find((f) => f.name === name));
          this.filterForm.get(name).setValue(json[this.entity][name]);
        });
      }

      this.applyFilters();
    }
  }

  applyFilters(): void {
    const filters = Object.entries(this.filterForm.value).reduce((res, [filterKey,filterVal]) => {
      if (filterVal === '' || filterVal === undefined) {
        return res;
      }

      if (this.filtersByType[filterKey] === 'datepicker' && filterVal['start'] && filterVal['end']) {
        return {
          ...res,
          [`${filterKey}_after`]: filterVal['start'].toISOString(),
          [`${filterKey}_before`]: filterVal['end'].toISOString()
        }
      }

      return {
        ...res,
        [filterKey]: filterVal
      }
    }, {})

    this.filterParams$.next(filters);
  }

  toggleFilters(filter): void {
    if (this.activeFilters.includes(filter?.id)) {
      this.activeFilters = this.activeFilters.filter((f) => f !== filter?.id);
      this.localStorageManaging(filter);
      this.filterForm.removeControl(filter?.filter_field);
    } else if (filter) {
      this.activeFilters.push(filter?.id);
      if (filter?.filter_type === 'datepicker') {
        this.filterForm.addControl(filter.filter_field, new FormGroup({
          start: new FormControl(new Date()),
          end: new FormControl(new Date()),
        }));
      } else if (filter) this.filterForm.addControl(filter?.filter_field, new FormControl(''))
    }
  }

  clear(filter, event: any) {
    if (this.filtersByType[filter] === 'datepicker') {
      this.filterForm.get(filter).setValue({start: undefined, end: undefined});
    } else this.filterForm.get(filter).setValue(undefined);

    this.applyFilters();
  }

  removeFilter(filter, event) {
    this.toggleFilters(filter);
    this.applyFilters();
  }

  localStorageManaging(filter): void {
    const listParamStr = localStorage.getItem('list:param');

    if (listParamStr) {
      const json = JSON.parse(listParamStr);

      if (json[this.entity]) {
        delete json[this.entity][filter.filter_field];

        this.manageDatepickerValue(json, true);
        this.manageUrl(json);

        if (Object.keys(json[this.entity]).length === 0) {
          delete json[this.entity];
        }
      }

      if (Object.keys(json).length === 0) {
        localStorage.removeItem('list:param');
      } else localStorage.setItem('list:param', JSON.stringify(json));
    }
  }

  manageDatepickerValue(json: Object, deleteMode?: boolean) {
    Object.keys(json[this.entity]).filter((name) => name.includes('_after') || name.includes('_before')).forEach((date) => {
      const dateProp = date.replace(/_after|_before/gi, '');
      const period = date.includes('_after') ? 'start' : 'end';

      if (!deleteMode) {
        json[this.entity][dateProp] = {...json[this.entity][dateProp], [period]: new Date(json[this.entity][date])};
      }

      delete json[this.entity][date];
    })
  }

  manageUrl(json) {
    let queryArray = window.location.href.split(';');
    const base = queryArray.shift();

    if (Object.keys(json[this.entity]).length === 0) {
      window.history.pushState(null, null, base);
      return;
    }

    queryArray = queryArray.filter((query) => {
      return Object.keys(json[this.entity]).some((filter) => query.includes(filter));
    });

    if (queryArray.length > 0) {
      queryArray.unshift(base);
      const query = queryArray.join(';');

      window.history.pushState(null, null, query);
    } else window.history.pushState(null, null, base);
  }
}

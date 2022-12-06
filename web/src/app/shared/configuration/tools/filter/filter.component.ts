// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
/**
 * INSTRUCTIONS
 * For the filter to work correctly, you need to create a filter rules with IFilter stucture in filter parent component
 * "copy" of the BehaviourSubject with data for the table and pass it to the table. You must pass both the original
 * and the "copy" to the filter component
 */
import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { BaseDirective } from "../../../directives";
import { BehaviorSubject } from "rxjs";

export interface IFilter {
  id: number,
  name: string,
  display_name: string,
  filter_field: string,
  filter_type: FilterType,
  options?: IFilterOption[],
  active?: boolean,
}

export interface IFilterOption {
  id: number,
  name: string,
  display_name: string,
  value: any,
}

type FilterType = 'list' | 'input' | 'datepicker';

@Component({
  selector: 'app-filter',
  templateUrl: './filter.component.html',
  styleUrls: ['./filter.component.scss'],
})
export class FilterComponent extends BaseDirective implements OnInit, OnDestroy {
  filterForm = new FormGroup({});
  availableFilters: any[];
  activeFilters: number[] = [];
  filtersByType = {};
  backupData: any;
  freezeBackupData: boolean = false;
  externalChanges: boolean = false;
  @Input() filterList: IFilter[] = [];
  @Input() externalData: BehaviorSubject<any>;
  @Input() innerData: BehaviorSubject<any>;

  get filters() {
    return this.filterList.filter((filter) => (this.activeFilters?.includes(filter.id)));
  }

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

    this.externalData.subscribe((values: any) => {
      this.externalChanges = true;
      this.freezeBackupData = false;

      if (this.externalChanges && values) {
        this.innerData.next(values);

        this.innerData.subscribe((values: any) => {
          if (!this.backupData || !this.freezeBackupData) {
            this.backupData = values;
            this.freezeBackupData = false;
          }

          if (this.externalChanges) {
            this.externalChanges = false;
            this.applyFilters();
          }
        })
      }
    });
  }

  clear(filter, event: any) {
    if (this.filtersByType[filter] === 'datepicker') {
      this.filterForm.get(filter).setValue({start: undefined, end: undefined});
    } else this.filterForm.get(filter).setValue(undefined);
    this.innerData.next(this.backupData);
    event.preventDefault();
    event.stopPropagation();
  }

  removeFilter(filter, event) {
    this.toggleFilters(filter);
    this.applyFilters();
    event.preventDefault();
  }

  setDate(event) {
    if (event.value) {
      event.value.setHours(23, 59, 59, 999);
      this.applyFilters();
    }
  }

  applyFilters() {
    const filters = this.filterForm.value;

    if (Object.keys(filters).filter((f) => {
      if (filters[f] === '' || filters[f] === undefined) {
        delete filters[f];
        return false;
      } else return true;
    }).length === 0) {
      this.innerData.next(this.backupData);
      return;
    }

    let data = this.backupData?.results?.filter((item) => {
      for (let key in filters) {
        if (this.filtersByType[key] === 'list') {
          if (item[key] === undefined || item[key] !== filters[key]) {
            return false;
          }
        }
      }

      return true;
    });

    if (this.filters.some((f) => f.filter_type === 'input' && filters[f.filter_field])) {
      data = data.filter((item) => {
        return Object.keys(filters).filter((f) => this.filtersByType[f] === 'input').every((i) => {
          if (i.includes('/')) {
            let nestedKey = i.split('/');

            if (item[nestedKey[0]][nestedKey[1]] !== undefined &&
              item[nestedKey[0]][nestedKey[1]] !== null &&
              item[nestedKey[0]][nestedKey[1]] !== '' &&
              item[nestedKey[0]][nestedKey[1]].toLowerCase().includes(filters[i].toLowerCase())) {
              return true;
            }
          } else {
            if (item[i] !== undefined && item[i] !== null && item[i] !== '' && item[i].toLowerCase().includes(filters[i].toLowerCase())) {
              return true;
            }
          }
        })
      })
    }

    if (this.filters.some((f) => f.filter_type === 'datepicker' && filters[f.filter_field].end)) {
      data = data.filter((item) => {
        return Object.keys(filters).filter((f) => this.filtersByType[f] === 'datepicker').every((i) => {
          if (item[i] !== undefined && item[i] !== null && (filters[i].start < new Date(item[i]) && new Date(item[i]) < filters[i].end)) {
            return true;
          }
        })
      })
    }

    let count = this.activeFilters.length === 0 ? this.backupData.count : data.count;
    this.freezeBackupData = true;
    this.innerData.next({...this.backupData, count, results: data});
  }

  clearButtonVisible(field) {
    const value = this.filterForm?.getRawValue()[field];
    return this.filtersByType[field] !== 'datepicker' && (value || (typeof value === 'boolean' && !value));
  }

  toggleFilters(filter) {
    if (this.activeFilters.includes(filter.id)) {
      this.activeFilters = this.activeFilters.filter((f) => f !== filter.id);
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

  datepickerGroup(controlName): FormGroup {
    return this.filterForm.get(controlName) as FormGroup;
  }
}

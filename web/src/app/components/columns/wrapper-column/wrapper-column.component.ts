import { Component, Input, OnInit } from '@angular/core';

/*
* Component wrapper for columns
* If you need to change color of column value - use type 'color'
* If you need to make sure that long names will be trimmed to the column size -  use type 'text-substr'
*/

@Component({
  selector: 'app-wrapper-column',
  templateUrl: './wrapper-column.component.html',
  styleUrls: ['./wrapper-column.component.scss']
})
export class WrapperColumnComponent implements OnInit {

  @Input() type: string[];

  row: any;
  column: any;
  red: string[] = ['delete', 'fail'];
  orange: string[] = ['update', 'denied'];
  green: string[] = ['create', 'success'];

  constructor() { }

  get columnName(): string {
    return this.column?.label?.toLowerCase()?.replace(' ', '_');
  }

  ngOnInit(): void {}

  getWrapperClass() {
    return this.type.map(value => {
      switch(value) {
        case 'color':
          return this.getColorClass();
        case 'text-substr':
          return 'text-ellipsed';
      }
    }).join(' ');
  }

  getColorClass() {
    const value = this.row[this.columnName];

    if (this.red.includes(value)) {
      return 'red';
    } else if (this.orange.includes(value)) {
      return 'orange';
    } else if (this.green.includes(value)) {
      return 'green';
    }
  }
}

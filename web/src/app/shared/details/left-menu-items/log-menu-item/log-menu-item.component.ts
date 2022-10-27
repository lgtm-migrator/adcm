import { Component } from '@angular/core';

import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';
import { BaseEntity, Job } from '@app/core/types';

@Component({
  selector: 'app-log-menu-item',
  template: `
    <a mat-list-item
       [appForTest]="'tab_' + link"
       [routerLink]="link"
       routerLinkActive="active"
    >
      <span>{{ label }}</span>&nbsp;

      <button mat-icon-button
              color="primary"
              (click)="download()"
      >
        <mat-icon>cloud_download</mat-icon>
      </button>
    </a>
  `,
  styles: ['a span { white-space: nowrap; }'],
})
export class LogMenuItemComponent extends MenuItemAbstractDirective<BaseEntity> {

  download() {
    const isLoggedIn = localStorage.getItem('auth');

    if (isLoggedIn) {
      if (this.data?.logId) {
        const file = (this.entity as Job).log_files.find(job => job.id === this.data.logId);
        if (file) {
          location.href = file.download_url;
        } else {
          throw new Error('Log file not found!');
        }
      } else {
        throw new Error('Log id isn\'t provided!');
      }
    } else {
      window.location.href = "/login";
    }
  }

}

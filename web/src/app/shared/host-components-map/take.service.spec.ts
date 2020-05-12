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
import { HttpClientModule } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ApiService } from '../../core/api';
import { reducers } from '../../core/store';
import { StoreModule } from '@ngrx/store';

import { TakeService } from './take.service';
import { CompTile } from './types';

describe('HostComponentsMap :: TakeService', () => {
  beforeEach(() =>
    TestBed.configureTestingModule({
      imports: [
        HttpClientModule,
        StoreModule.forRoot(reducers, {
          runtimeChecks: {
            strictStateImmutability: true,
            strictActionImmutability: true,
            strictStateSerializability: true,
            strictActionSerializability: true
          }
        })
      ],
      providers: [ApiService, TakeService]
    })
  );

  it('should be created', () => {
    const service: TakeService = TestBed.inject(TakeService);
    expect(service).toBeTruthy();
  });

  const mockCompTile = new CompTile({
    id: 1,
    service_id: 2,
    service_name: 'test_service',
    service_state: 'created',
    name: 'test',
    display_name: 'test',
    status: 16,
    constraint: '',
    monitoring: 'passive'
  });

  it('validateConstraints fn should be null if argument is null', () => {
    const service: TakeService = TestBed.inject(TakeService);
    expect(service.validateConstraints(mockCompTile)(null)).toBeNull();
  });
});

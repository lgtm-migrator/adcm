#!/bin/python3

from pathlib import Path
from typing import Iterable, List, Optional, Dict, Type, Union, TypeVar, Tuple

import yaml
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Provider

BUNDLES_DIR = Path(__file__).parent / 'bundles'


# Cluster, Provider, Host, Bundle
TopLevelObject = TypeVar('TopLevelObject')


class ADCMSetup:
    _DEFAULT_SETUP_DIR = Path(__file__).parent / 'setups'
    _APPROPRIATE_SUFFIXES = ('.yaml', '.yml')
    _CLEANING_ORDER = (Cluster, Host, Provider, Bundle)

    client: ADCMClient
    setup: Optional[dict]

    created_objects: Dict[Type[TopLevelObject], List[TopLevelObject]]
    entities_map: Dict[Tuple[Type[TopLevelObject], str], TopLevelObject]

    def __init__(self, client: ADCMClient):
        self.client = client
        self.setup = None
        self.created_objects = {obj_type: [] for obj_type in (Cluster, Provider, Host, Bundle)}
        self.entities_map = {}

    # Upload setup file || Prepare setup

    def setup_from_file(self, setup_name: str, custom_dir: Optional[str] = None):
        self.load_setup_file(setup_name, custom_dir)
        self._create_entities()

    def load_setup_file(self, setup_name: str, custom_dir: Optional[str] = None) -> None:
        setup_file = self._find_setup_file(custom_dir or self._DEFAULT_SETUP_DIR, setup_name)
        with setup_file.open('r') as file:
            self.setup = yaml.safe_load(file)

    def _find_setup_file(self, setup_dir: Optional[Union[str, Path]], setup_name: str) -> Path:
        setup_file = Path(setup_dir) / setup_name

        if setup_file.exists():
            return setup_file

        if setup_file.suffix:
            raise ValueError(
                'Provided setup name contains suffix, but was failed to be found in setup directory.\n'
                f'Setup name: {setup_name}\n'
                f'Directory name: {setup_dir}\n'
            )

        for suffix in self._APPROPRIATE_SUFFIXES:
            path_with_suffix = setup_file.with_suffix('').with_suffix(suffix)
            if path_with_suffix.exists():
                return path_with_suffix

        raise ValueError(
            f'File with setup could not be found in {setup_dir} '
            f'with any of available suffixes: {", ".join(self._APPROPRIATE_SUFFIXES)}'
        )

    # Run setup

    def _create_entities(self):
        entities_to_create = {**self.setup['entities']}

        bundles_to_upload = entities_to_create.pop('bundles', None)
        if bundles_to_upload is None:
            raise KeyError(
                'Current implementation does not support pre-uploaded bundles.\n'
                'Provide "bundles" entry to "entities" section of your setup file.'
            )
        self._upload_bundles(bundles_to_upload)

        for plural_type, definitions in entities_to_create.items():
            create_method = getattr(self, f'_create_{plural_type}', None)
            assert create_method, f'Objects of type {plural_type} are not supported'
            create_method(definitions)

    def _upload_bundles(self, bundles):
        assert isinstance(bundles, Iterable), '"bundles" section should be a list'
        assert all(isinstance(b, str) for b in bundles), 'Bundles should be strings'

        for bundle_name in bundles:
            # TODO try to call "on_conflict" if upload fails
            bundle = self.client.upload_from_fs(str(BUNDLES_DIR / bundle_name))
            self._register(bundle, bundle_name)

    def _create_clusters(self, definitions):
        # TODO add validation on upload
        required_keys = {'from', 'name'}
        assert all(
            isinstance(d, dict) and required_keys.issubset(d.keys()) for d in definitions
        ), f'All cluster definitions should be dicts and have keys: {required_keys}'

        for definition in definitions:
            bundle = self._get_entity(Bundle, definition['from'])
            new_cluster: Cluster = bundle.cluster_create(name=definition['name'])
            for config_group in definition.get('config_groups', ()):
                new_cluster.group_config_create(name=config_group['name'])
            self._register(new_cluster, definition['name'])

    def _register(self, entity: TopLevelObject, identifier: str):
        self.created_objects[entity.__class__].append(entity)
        self.entities_map[(entity.__class__, identifier)] = entity

    def _get_entity(self, obj_type: Type[TopLevelObject], identifier: str) -> TopLevelObject:
        return self.entities_map[(obj_type, identifier)]

    def _get_created(self, obj_type: Type[TopLevelObject], **attribute) -> TopLevelObject:
        suitable_object = next(
            filter(
                lambda obj: all(getattr(obj, attr_key, None) == value for attr_key, value in attribute.items()),
                self.created_objects.get(obj_type, ()),
            ),
            None,
        )

        if not suitable_object:
            raise IndexError(f'Object of type {obj_type} with attributes: {attribute} was not found')

        return suitable_object

    # Cleanup

    def clean_existing(self):
        for object_type in self._CLEANING_ORDER:
            for obj in getattr(self.client, f'{object_type.__name__.lower()}_list')():
                obj.delete()

    def clean_created(self):
        for object_type in self._CLEANING_ORDER:
            for obj in self.created_objects.pop(object_type, ()):
                obj.delete()


if __name__ == '__main__':
    personal_setup_file = Path(__file__).parent / '.setup'
    # too raw
    if personal_setup_file.exists():
        with personal_setup_file.open('r') as file:
            setup_name = file.readlines()[0].strip()
    else:
        raise NotImplementedError('Only ".setup" file is now supported')

    setup = ADCMSetup(ADCMClient(url='http://127.0.0.1:8000', user='admin', password='admin'))
    setup.clean_existing()
    setup.setup_from_file(setup_name)

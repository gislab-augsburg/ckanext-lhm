[![Tests](https://github.com/MandanaMoshref/ckanext-lhm/actions/workflows/test.yml/badge.svg)](https://github.com/MandanaMoshref/ckanext-lhm/actions)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
![Github open issues](https://img.shields.io/github/issues/MandanaMoshref/ckanext-lhm)
![GitHub forks](https://img.shields.io/github/forks/MandanaMoshref/ckanext-lhm?style=social)
![GitHub Repo stars](https://img.shields.io/github/stars/MandanaMoshref/ckanext-lhm?style=social)

# ckanext-lhm
This extension is built exclusively to meet the requirements of the City of Munich. This extension is a work in progress, the following explanations cover the current state of development and the features included.

Table of Contents:
- [ckanext-lhm](#ckanext-lhm)
  - [Features](#features)
  - [Requirements](#requirements)
    - [Dependencies \& Settings](#dependencies--settings)
  - [Installation](#installation)
  - [Config settings](#config-settings)
  - [Developer installation](#developer-installation)
  - [Tests](#tests)
  - [License](#license)
  - [Copyright](#copyright)


## Features
- Action `user_create`: this function automatically adds each newly added user to all groups as a member. It is possible to change the role to other group roles. In this case in `ckan.ini` the following attribute should be set:
    ```ini
    ckan.lhm.group_role = member
    ```
- Helpers offers various helpers functions. Some for being used in templates such as lhm.usage_info() to get the configurables and some as functions to be used in templates such as `user_info()`.
- cli offers one command line for creating the pre-defined groups.
  ```sh
    ckan -c /etc/ckan/default/ckan.ini grouphierarchy init_data
  ``` 
- theme_templates / theme_temlates_2.9.9 offers the templates for lhm styling/theme.
  

## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?          |
| --------------- | ---------------------|
| 2.8 and earlier | not tested           |
| 2.9             | yes, tested, works   |
| 2.10            | On-going development |

### Dependencies & Settings   

This extension works together with a selection of other extensions. Without those extensions, ckanext-lhm cannot fully be executed. The dependent extensions are:

:heavy_exclamation_mark: These extensions are option. Without them no errors will come up but it means the lhm_schema.yaml will not work as it is.
> [!note]
> <sub>*The following extensions are required to have the description of the attributes in a dataset. Example: An excel file with 5 columns. Each column has a name and a data type. To make them understandable to the user, it is necessary to provide a data dictionary with an explanation of what the column name means, what data it contains and what data type it has.*</sub>
 - [Datastore](https://docs.ckan.org/en/latest/maintaining/datastore.html)
 - [ckanext-xloader](https://github.com/ckan/ckanext-xloader/)
 - [ckanext-resourcedictionary](https://github.com/keitaroinc/ckanext-resourcedictionary)

:bangbang: These extensions are required. Without this extensions the ckanext-lhm cannot be executed.

 - [ckanext-scheming](https://github.com/ckan/ckanext-scheming/)
 - [ckanext-composite](https://github.com/EnviDat/ckanext-composite)
 - [ckanext-hierarchy](https://github.com/ckan/ckanext-hierarchy/)

------------------
![*The order of pludings matter*](https://img.shields.io/badge/ckan.plugins-ORDER.MATTERS-darkred)

The order of pludings in this ckanext matters. Deponding on the collection of extensions used for a ckan this list may extended. Below is the list of extensions with which `lhm lhm_theme` are tested 
```ini
ckan.plugins = ... scheming_datasets composite hierarchy_display hierarchy_form lhm lhm_theme hierarchy_group_form resourcedictionary datastore xloader 
```
----------------------
:heavy_check_mark:


**TODO:** The code was originally written for version 2.10. During the development of the lhm_theme, the ckan version was downgraded to 2.9.9. Therefore, from a certain point in time, development was only continued for version 2.9.9. In order for the extension to run on version 2.10, it is necessary to continue developing the theme and also to fully test the newly developed functionality with CKAN v2.10.
- [ ] update the `theme_templates`
- [ ] Test the whole extension with CKAN v2.10

## Installation

To install ckanext-lhm:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv
    ```sh
    git clone git@github.com:MandanaMoshref/ckanext-lhm.git
    cd ckanext-lhm
    pip install -e .
    pip install -r requirements.txt
    ```

3. Add extension modules to the `ckan.plugins` setting in your CKAN config file (by default the config file is located at `/etc/ckan/default/ckan.ini`). 
   - Add `lhm` in order to have the related LHM Schema and concept for the catalog (such as Main Groups, Topics, etc.)
   - Add `lhm_theme` in order to have the LHM styling for the main CKAN interface

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Config settings
In order to use the provided modules the following configurations are necessary:

```ini
# Each of the plugins is optional depending on your use
ckan.plugins = lhm lhm_theme

#-------------------------------------
#   Configurations for module "lhm"
#-------------------------------------
#   module-path:file to schemas being used
#   Here an absolute or relative path can be also provided e.g. /etc/ckan/schemas/lhm_dataset.yaml
scheming.dataset_schemas = ckanext.lhm:schemas\lhm_dataset.yaml

#   Preset files may be included as well. The default preset setting is:
scheming.presets = ckanext.scheming:presets.json
                   ckanext.composite:presets.json

#-------------------------------------
#   Configurations for module "lhm_theme"
#-------------------------------------
#   Followings are global and specific configurations for the styling of lhm catalog
ckan.site_title = "TITLE"
ckan.site_logo = lhm
ckan.site_intro_text = "INTRO TEXT"
ckan.site_description = "CATALOG DESCRIPTION" 
ckan.favicon = favicon.ico

lhm.usage_info = "TERSM OF USE"
lhm.contact_email = mailto:"EMAIL ADRESS"
lhm.github = "GITHUB REPO"
lhm.version_info = "CKAN VERSION INFO"

#   Although the extension provides translation but it is not fully implemented and therefore at the best the extension works when there is only one language as default
# Internationalisation Settings
ckan.locale_default = de
```

In order to use the module `lhm_theme` following command line should be executed:
  ```sh
    ckan -c /etc/ckan/default/ckan.ini grouphierarchy init_data
  ``` 
  This creates all pre-defined groups which are necessary for LHM Concept.

**TODO:** To convert all the configurable features into configurable attribute for ckan.ini

## Developer installation

To install ckanext-lhm for development, activate your CKAN virtualenv and
do:

    git clone git@github.com:MandanaMoshref/ckanext-lhm.git
    cd ckanext-lhm
    python setup.py develop
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini ckanext/lhm/tests

Please make sure that you have provided a correct path for your test-core.ini in the `test.ini` file

```
[app:main]
use = config:../ckan/test-core.ini
```

## License
This CKAN extension is licensed under the Affero General Public License (AGPL) v3.0. This means that you are free to modify, distribute, and use this software, as long as any modifications and derived works are also licensed under the AGPL.

The AGPL is a strong copyleft license, which ensures that all modifications and derivative works based on this extension are open source. The key requirement of the AGPL is that if you run a modified program on a server and let other users communicate with it there, you must also make the modified source available to those users.

For more details, see the [LICENSE](LICENSE) file in this repository or [read the AGPL v3.0 license terms online](https://www.gnu.org/licenses/agpl-3.0.html).

## Copyright

Copyright belongs to commit authors.

<!--
## Releasing a new version of ckanext-lhm

If ckanext-lhm should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in the `setup.py` file. See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers) for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:

    pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version:

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI:

       twine upload dist/*

5. Commit any outstanding changes:

       git commit -a
       git push

6. Tag the new release of the project on GitHub with the version number from
   the `setup.py` file. For example if the version number in `setup.py` is
   0.0.1 then do:

       git tag 0.0.1
       git push --tags
-->

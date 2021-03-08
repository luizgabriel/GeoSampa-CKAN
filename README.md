# GeoSampa/CKAN

A command line script for importing all [GeoSampa](http://geosampa.prefeitura.sp.gov.br/) data and export automatically to any CKAN datastore.

<table>
  <tr>
    <td>
      <img src="https://user-images.githubusercontent.com/7469145/110332696-6ef6fb00-7fff-11eb-985f-5b5b961016c2.png" alt="Migration result" />
    </td>
    <td>
      <img src="https://user-images.githubusercontent.com/7469145/110332824-9c43a900-7fff-11eb-938a-6c41b55fc643.png" alt="Package example" />
    </td>
  </tr>
</table>


# How to use
```
Usage:
  geosampa.py import [--output=<import-output>] [--theme=<filter-theme>] [--sub-theme=<filter-sub-theme>] [--host=<geosampa-host>]
  geosampa.py export ckan [--input=<export-input>] [--site=<ckan-site>] [--public] [--api-key=<ckan-api-key>] [--organization=<ckan-org>]
  geosampa.py (-h | --help)
  geosampa.py --version
  
Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --output=<import-output>      GeoSampa files will be downloaded to [default: ./].
  --theme=<filter-theme>        Filter GeoSampa Themes.
  --sub-theme=<filter-theme>    Filter GeoSampa Sub-themes.
  --host=<geosampa-host>        GeoSampa files will be downloaded to [default: http://geosampa.prefeitura.sp.gov.br].
  --site=<ckan-site>            Your ckan site. i.e.: https://dataurbe.appcivico.com/
  --api-key=<ckan-api-key>      Your CKAN API Key.
  --organization=<ckan-org>     The CKAN Organization the datasets will be created
  --public                      Create public datasets
```

## Importing from GeoSampa

```
python geosampa.py import --output=./files
```
### Optional Filtering
You can also filter the downloaded files by theme and sub-theme:

```
python geosampa.py import --output=./files --theme="01_Limites Administrativos"
```

## Exporting to CKAN

```
python geosampa.py export ckan --input=./files
```
The script will ask your CKAN API Key, the CKAN site url and the organization which all datasets/packages will be registered.

![image](https://user-images.githubusercontent.com/7469145/110338009-48d45980-8005-11eb-9d1d-39e5a3659dea.png)

Optionally, you can specify all information directly on the command line with:
```
python geosampa.py export ckan --input=./files --site=https://dataurbe.appcivico.com/ --api-key=[API_KEY] --organization=saopaulo
```

> ## Important!
> By default, all packages are created/updated as "private". 
> 
> If you rather having then as public, you'll need to specify the `--public` option flag.


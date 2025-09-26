"""Dataclasses describing the most common SIM API resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ProjectInstitutionLink:
    """Link from a project name to its institution resource."""

    projektname: str
    einrichtungs_id: str
    link: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectInstitutionLink":
        return cls(
            projektname=data.get("projektname", ""),
            einrichtungs_id=data.get("einrichtungsId", ""),
            link=data.get("link", ""),
        )


@dataclass(slots=True)
class InstitutionAddress:
    """A physical address block associated with an institution."""

    typ: Optional[str] = None
    strasse: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: Optional[str] = None
    postfach: Optional[str] = None
    adresszusatz: Optional[str] = None
    co: Optional[str] = None
    person: Optional[str] = None
    kennung: Optional[str] = None
    postverteilschluessel: Optional[str] = None
    adressat1: Optional[str] = None
    adressat2: Optional[str] = None
    adressat3: Optional[str] = None
    adressat4: Optional[str] = None
    name: Optional[str] = None
    geerbt: Optional[bool] = None
    person_link: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstitutionAddress":
        return cls(
            typ=data.get("typ"),
            strasse=data.get("strasse"),
            plz=data.get("plz"),
            ort=data.get("ort"),
            land=data.get("land"),
            postfach=data.get("postfach"),
            adresszusatz=data.get("adresszusatz"),
            co=data.get("co"),
            person=data.get("person"),
            kennung=data.get("kennung"),
            postverteilschluessel=data.get("postverteilschluessel"),
            adressat1=data.get("adressat1"),
            adressat2=data.get("adressat2"),
            adressat3=data.get("adressat3"),
            adressat4=data.get("adressat4"),
            name=data.get("name"),
            geerbt=data.get("geerbt"),
            person_link=data.get("person_link"),
        )


@dataclass(slots=True)
class Institution:
    """Details about an institution within the LRZ system."""

    lrz_id: str
    name: Optional[str] = None
    parent_ids: List[str] = field(default_factory=list)
    parent_links: List[str] = field(default_factory=list)
    bezeichnung: Optional[str] = None
    nutzerklasse: Optional[str] = None
    mwnintern: Optional[str] = None
    kostenabrechnung: List[str] = field(default_factory=list)
    einrichtungsart: Optional[str] = None
    einrichtungstyp: Optional[str] = None
    adsorgpraefix: Optional[str] = None
    status: Optional[str] = None
    importiert: Optional[str] = None
    anschriften: List[InstitutionAddress] = field(default_factory=list)
    chef_lrz_id: Optional[str] = None
    chef_links: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Institution":
        return cls(
            lrz_id=data.get("LRZid", ""),
            name=data.get("name"),
            parent_ids=list(data.get("parent_lrzId", []) or []),
            parent_links=list(data.get("parent_link", []) or []),
            bezeichnung=data.get("bezeichnung"),
            nutzerklasse=data.get("nutzerklasse"),
            mwnintern=data.get("mwnintern"),
            kostenabrechnung=list(data.get("kostenabrechnung", []) or []),
            einrichtungsart=data.get("einrichtungsart"),
            einrichtungstyp=data.get("einrichtungstyp"),
            adsorgpraefix=data.get("adsorgpraefix"),
            status=data.get("status"),
            importiert=data.get("importiert"),
            anschriften=[InstitutionAddress.from_dict(entry) for entry in data.get("anschriften", [])],
            chef_lrz_id=data.get("chef_lrzId"),
            chef_links=list(data.get("chef_link", []) or []),
        )


@dataclass(slots=True)
class Person:
    """Representation of an LRZ person."""

    lrz_id: str
    benutzername: Optional[str] = None
    anrede: Optional[str] = None
    rufname: Optional[str] = None
    nachname: Optional[str] = None
    titel_pre: Optional[str] = None
    titel_post: Optional[str] = None
    geschlecht: Optional[str] = None
    kennungen: List[str] = field(default_factory=list)
    status: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Person":
        return cls(
            lrz_id=data.get("LRZid", ""),
            benutzername=data.get("benutzername"),
            anrede=data.get("anrede"),
            rufname=data.get("rufname"),
            nachname=data.get("nachname"),
            titel_pre=data.get("titelPre"),
            titel_post=data.get("titelPost"),
            geschlecht=data.get("geschlecht"),
            kennungen=list(data.get("kennungen", []) or []),
            status=data.get("status"),
        )


@dataclass(slots=True)
class User:
    """Representation of a SIM user entry."""

    kennung: str
    lrz_id: Optional[str] = None
    status: Optional[str] = None
    status_num: Optional[int] = None
    validpwd: Optional[int] = None
    uid: Optional[str] = None
    gid: Optional[str] = None
    projekt: Optional[str] = None
    kennungstyp: Optional[str] = None
    daten: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            kennung=data.get("kennung", ""),
            lrz_id=data.get("mwnlrzid"),
            status=data.get("status"),
            status_num=data.get("status_num"),
            validpwd=data.get("validpwd"),
            uid=data.get("uid"),
            gid=data.get("gid"),
            projekt=data.get("projekt"),
            kennungstyp=data.get("kennungstyp"),
            daten=data.get("daten", {}),
        )

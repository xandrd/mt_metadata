# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 10:33:27 2021

:copyright: 
    Jared Peacock (jpeacock@usgs.gov)

:license: MIT

"""
from mt_metadata.utils.mt_logger import setup_logger

# =============================================================================
# Translate between metadata and inventory: mapping dictionaries
# =============================================================================
class BaseTranslator:
    """
    Base translator for StationXML <--> MT Metadata
    
    """

    def __init__(self):
        self.logger = setup_logger(f"{__name__}.{self.__class__.__name__}")
        self.xml_translator = {
            "alternate_code": None,
            "code": None,
            "comments": None,
            "data_availability": None,
            "description": None,
            "historical_code": None,
            "identifiers": None,
            "restricted_status": None,
            "source_id": None,
        }

        self.mt_translator = self.flip_dict(self.xml_translator)

    @staticmethod
    def flip_dict(original_dict):
        """
        Flip keys and values of the dictionary
        
        Need to take care of duplicate names and lists of names
        
        :param original_dict: original dictionary
        :type original_dict: dict
        :return: reversed dictionary
        :rtype: dictionary
    
        """
        flipped_dict = {}

        for k, v in original_dict.items():
            if v in [None, "special"]:
                continue
            if k in [None]:
                continue
            if isinstance(v, (list, tuple)):
                # bit of a hack, needs to be more unique.
                for value in v:
                    flipped_dict[value] = k
            else:
                flipped_dict[str(v)] = k

        return flipped_dict

    @staticmethod
    def read_xml_comment(comment):
        """
        read stationxml comment
        
        Assuming that separate comments are split by ':' and separated 
        by a comma. 
        
        """
        
        key = comment.subject.strip().replace(" ", "_").lower()
        
        def parse(comment_string, filled={}):
            """
            Recursively parse a comment string trying to adhere to the 
            original syntax of the comment.  Expecting a dictionary type
            string
            
            'a: b, c:d' -> {'a': 'b', 'c':'d'}
            
            but sometimes looks like
            
            'a: b:c, d:e' -> {'a': 'b:c', 'd':'e'}
            
            """
            k, *other = comment_string.split(":", 1)
            if other: 
                other = other[0]
                key = k
                if other.find(':') >= 0 and other.find(",") >= 0:
                    if other.find(':') < other.find(','):
                        if other.count(':') > 1:
                            value, *maybe = other.split(',', 1)
                            filled[key] = value.strip().replace(':', '--')
                            if maybe:
                                filled = parse(maybe[0].strip(), filled)
                        else:
                            filled[key] = other.replace(':', '--')
                    else:
                        value, *maybe = other.split(',', 1)
                        filled[key] = value.strip()
                        if maybe:
                            filled = parse(maybe[0].strip(), filled)
                elif other.find(':') > 0:
                    value, *maybe = other.split(':', 1)
                    filled[key] = value.strip()
                else:
                    filled[key] = other.strip()
                        
            else:
                filled[k] = None
            return filled
        
        # if the string is dictionary like, parse, otherwise skip
        if ':' in comment.value:
            value = parse(comment.value)
        else:
            value = comment.value

        return key, value

    @staticmethod
    def read_xml_identifier(identifiers):
        """
        Read stationxml idenfier, which is a list of doi numbers, make
        it into a string without the doi
        
        :param doi: DESCRIPTION
        :type doi: TYPE
        :return: DESCRIPTION
        :rtype: TYPE

        """
        return ", ".join([ii.strip().split("DOI:")[1] for ii in identifiers])

    def get_comment(self, comments, subject):
        """
        Get the correct comment from a list of comments
        
        :param comments: list of :class:`obspy.core.inventory.Comments`
        :type comments: list
        :param subject: subject heading to get
        :type subject: string
        :return: the corresponding comment
        :rtype: :class:`obspy.core.inventory.Comments`

        """

        for comment in comments:
            if comment.subject == subject:
                return comment

        self.logger.info(f"Could not find {subject} in the given list of comments.")
        return None
    
    def xml_to_mt(self, value):
        pass
    
    def mt_to_xml(self, value):
        pass
    

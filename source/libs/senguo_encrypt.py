import binascii

from Crypto.Cipher import DES


class EncryptBase():
    '''
        调用示例
        加密:SimpleEncrypt.encrypt('10930')
            返回:'41c836605df56a81'
        解密:SimpleEncrypt.decrypt('41c836605df56a81')
            返回:'10930'
    '''
    @classmethod
    def pad(cls, text):
        '''
            length需和key长度相等
        '''
        while len(text) % cls.crypt_len != 0:
            text += " "
        return text

    @classmethod
    def encrypt(cls, text):
        '''
            参数: text-待加密字符串
                  key-DES需要的秘钥
        '''
        if not isinstance(text,str):
            text = str(text)
        des = DES.new(cls.crypt_key, DES.MODE_ECB)
        padded_text = cls.pad(text)
        encrypted_text = des.encrypt(padded_text)
        return binascii.hexlify(encrypted_text).decode()

    @classmethod
    def decrypt(cls, text):
        if not isinstance(text,str):
            text = str(text)
        try:
            encrypted_text = binascii.unhexlify(text)
        except:
            return "0"
        des = DES.new(cls.crypt_key, DES.MODE_ECB)
        return des.decrypt(encrypted_text).decode().strip()

    @classmethod
    def decrypt_to_int(cls,text):
        try:
            text = int(cls.decrypt(text))
        except:
            text = 0
        return text


class SimpleEncrypt(EncryptBase):
    '''
        用于采购系统数据加密
    '''
    crypt_key = "CGkiedbs"
    crypt_len = 8

class SgSimpleEncrypt(EncryptBase):
    '''
        用于与零售系统进行数据交互
    '''
    crypt_key = "s0&Kp#HF"
    crypt_len = 8
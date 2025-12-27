create table pan_cookies
(
    id              int auto_increment comment '主键ID'
        primary key,
    pan_type        varchar(20)                          not null comment '网盘类型: baidu/quark',
    cookie          text                                 not null comment 'Cookie字符串',
    is_active       tinyint(1) default 1                 null comment '是否启用',
    last_check_time datetime                             null comment '最后检查时间',
    check_status    varchar(50)                          null comment '检查状态: valid/invalid/unknown',
    check_error     text                                 null comment '检查错误信息',
    created_at      datetime   default CURRENT_TIMESTAMP null comment '创建时间',
    updated_at      datetime   default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP comment '更新时间',
    constraint uk_pan_type
        unique (pan_type) comment '同类型网盘只保留一个Cookie'
)
    comment '网盘Cookie管理表' charset = utf8mb4;

INSERT INTO file_link_monitor_v2.pan_cookies (id, pan_type, cookie, is_active, last_check_time, check_status, check_error, created_at, updated_at) VALUES (1, 'baidu', 'BAIDUID=29F8A9F9ED335ED512B1471B22CE89E0:FG=1; BAIDUID_BFESS=29F8A9F9ED335ED512B1471B22CE89E0:FG=1; PANWEB=1; BIDUPSID=29F8A9F9ED335ED512B1471B22CE89E0; PSTM=1764809630; H_PS_PSSID=60271_63145_65314_66118_66216_66191_66196_66165_66280_66268_66393_66515_66529_66558_66584_66578_66590_66601_66605_66641_66647_66663_66676_66686_66689_66720_66745_66754_66784_66793_66803_66802_66599; ZFY=jfLIkUHeox9wwLBVmHHhvN1hAM0:BomG7j0Uug30AXB8:C; newlogin=1; ploganondeg=1; csrfToken=PW8iEzTufit-4GtCTeSUQhtJ; ppfuid=FOCoIC3q5fKa8fgJnwzbE0LGziLN3VHbX8wfShDP6RCsfXQp/69CStRUAcn/QmhIlFDxPrAc/s5tJmCocrihdwitHd04Lvs3Nfz26Zt2holplnIKVacidp8Sue4dMTyfg65BJnOFhn1HthtSiwtygiD7piS4vjG/W9dLb1VAdqPDGlvl3S9CENy8XO0gBHvcO0V6uxgO+hV7+7wZFfXG0MSpuMmh7GsZ4C7fF/kTgmt3jpj+McMorhe+Cj/9lStSBwMLYHXX6sSySAfDc47AfQqYgheSYkz7BDnJkD5v5D41v2iwj13daM+9aWJ5GJCQM+RpBohGNhMcqCHhVhtXpVObaDCHgWJZH3ZrTGYHmi7XJB9z3y2o8Kqxep5XBCsuFKJEamDWP0B99HzIVbHvrePooLbKBIKSSHTndNj5TmhzHi2LCZ2gO1+19qyTSEpAFeLs4wygIv6m069lhsdmzQ+ReezgAmT3lwuMU1qOVEPQFXV1C8qyUqcAnBm7hcJuxcqfdReixTVTfT+miI3ZV5eQE96jz5eP/gEigLYjtZnrOQVr9TB3lK8L3WS99/Zr9ng7DJNA0zsRL0eZGEKF1aDRInbESzVqJcCK3XpGJOV/zZ6wkf5f+PnYbtHcSvBB4lPdCgO/rhHbvTb7w1sYiN/Vk5/GFQKmYmpXiN4dJoe04sIEztQcQ/Sj8aeZwWg0mAteMeU9qyn6SoJvv6345Qt76XFBJWSgbZ6/F0ZRwCDo0NPL3fh6V0Qf84X0lHCGDVE6dnYotaYeW3myaaKjCupBJR/TSirmjBV2s3jnlQqvo9oPyP0nG9iKj3wRQUwzcav1VQU9Nb3SpOs6OnNPHvOBRFTC3dJt11rYxTmLu8GIDQxqMKltDwwpum3Juw8bhBgKsG2JlL29AEHRUoKNa0CrXiJwBTbsQ97ckDDWTffZfhpcog1PhEwkcbrqGW8fYF5mPl3xfYG6Tu9VE0I+fw7vVtkGN3nMKm3rd2mDkhNuquWLv5kuJDMwwerkeHUP9Bq7zt2A9A8E851l8QtBoQFIuWEGY3DMQGzE4fLtBnD2IBA1xgIrbF95h/aKYBNVXdvBhoLwXhcnXaiqXEpcvFQlonIv85FfaVbfEoKujQX2IBA1xgIrbF95h/aKYBNVh6Y0NjEKZ13xldTgKDiG2QRBJFTPsviSSEvgLGRO3YgGOv+/I3nwGp9q5hLF8/07goRUnieOy9WY3CCu1FKQrXv4Kl2tvhm/51VQHSSoTtFbHhSGlEKo+S0ciyUHoRYU; XFI=99cd36e0-dc76-11f0-836f-29e902b45a37; XFCS=E98094733FFB5868BE72F6A9FFFC911E55E9B82D806F45A4F13B36208220DD2E; XFT=ghEH7uQwcUv4NxEodQAAhBTv723Np9gUODUb7MjX8aI=; BDUSS=g0eHg3cE9MS2JPaEF-bm5Fc2Z0dm12YThFSERVYlRJbjktdVVrcDF3eXdNV3hwSVFBQUFBJCQAAAAAAQAAAAEAAABfSCmdvKvL2bj80MLXytS0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCkRGmwpERpd2; BDUSS_BFESS=g0eHg3cE9MS2JPaEF-bm5Fc2Z0dm12YThFSERVYlRJbjktdVVrcDF3eXdNV3hwSVFBQUFBJCQAAAAAAQAAAAEAAABfSCmdvKvL2bj80MLXytS0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCkRGmwpERpd2; STOKEN=80ae0f23fc60d90df511dc0a9c250a0c14f666f3b393a4131cfcabf1df38f005; BDCLND=rhiZ6qFTgMKn5sPss1%2BUBXQZdUn8znJ5cGwDM0C3vMY%3D; ndut_fmt=C30BDF417529EF017643AEC0C290553FD53BDFEC2F00D6EE88A53062D13C0453; ab_sr=1.0.1_YzY0ZTIxZTYxNTJjNjAyYjY4Y2I3MWJiNzYxMWE4NmU5Yjg1M2QzOWE1NmJmMGRkZGU2ZWViNWU2MmMzYWFmMDVlZWQ1M2M4ZWVjNzgzZTE3OWM2OGNkYmE5MDQwN2M4MDJiODVhZDFmM2Y4N2JjMjk5MDEyY2ViMTc0NGUwMWViYjM4ZmFhY2ZkMTE5ZTc0ZGRmM2E1M2E3MzM4MGI2NGI4YmVhOTkzMTIzMzExOWQ1YzQwOTc5YmYyODNjZGU2; PANPSC=10799957046963188896%3Au9Rut0jYI4ocyrHrO%2FcAv1cS2d9ns3O5C61tf8CKQkgw19TaLWf8SQXQ225L75l2wGQB7ARhquAd%2Bd6J43yXeQjn4HR56deP8oEHn5ZIJOmpKicp4leI%2Ft8WDKjdwpGvW1XX9xnmeNltcQe%2BbgwEaXWegKR%2ByMKcWP%2FWBC2ONxfgK8WiEYvObjEIKJQ%2BkRn2uPZxTPIZzXRtoLnfYC42LfDSJFbrrClxWDN81yfxsC8zfNvvSokn3AT5bdufxZCm5tFeRaakq8za51hMEGV028YD9Uwr9LAJ%2FCobuSJW7IR1Gv5h8iKvzz1o2HyqHDuYyCkP%2FabYFNrQJPTuxHgNcTp6OPEZDW9bd5ua1qgFiHY%3D', 1, null, 'unknown', null, '2025-12-19 14:13:13', '2025-12-19 14:13:13');
INSERT INTO file_link_monitor_v2.pan_cookies (id, pan_type, cookie, is_active, last_check_time, check_status, check_error, created_at, updated_at) VALUES (2, 'quark', 'b-user-id=8656abfd-ab9d-6d6a-e38f-c1b761d1c8e5; __sdid=AATOnqv5W6hIVXme8f/9wDsDrZLUWIfJgO02GFCf1/tpXs3cQY2aX2LjYS/zRNuADlQ=; _UP_A4A_11_=wb9d01614d704b3cafca764183c46eba; __kps=AASN593sgdaQrTW/48UVrnOD; __ktd=r4AuCjAEcKjUxTlg5xJB1A==; __uid=AASN593sgdaQrTW/48UVrnOD; __pus=ac2712c15667902d0f3f6ce5a122cb14AARwAVc/Dvm9mk6cev7rxG7ra/IomTxYNEiRIKNWp7CWT7AxJ0RgZnAac+LCYKgTIgbCWhFmTqDL+rOL5DC2KaC3; __kp=1c058f40-d4de-11f0-86b1-c71b3f60f0b8; cs_xcustomer_switch_user_key=775393f9-c8e4-4769-b6fd-d21bd96303d8; kkpcwpea=qs_clear_res=1&a=a&uc_param_str=einibicppfmivefrlantcunwsssvjbktchnnsnddds&instance=kkpcwp&pf=145&self_service=true&plain_utdid=ZjnVno1H6aEDADkt9wvrZ9YM&system_ver=Darwin_26.0.1&channel_no=pckk%40other_ch&ve=3.23.2&sv=release; CwsSessionId=53010a9a-d797-4459-97e3-ebf42a05c8b8; xlly_s=1; __puus=6a62929f174e0614973df330331ff0f7AAT1PrfXNhk3Gxfuk1rMWgk8QKeT9mKduhwtcQkUJSVfjTvdxG7CbaoYHm8/WwIkCPjE1WbOVPHde0R6NojuBb10pYJLXZZRJOhp0Jsl+TiNnPGw+UGjAKftzSkkPgkJNTEAbHIn8PbJ/vCSC9UOdhHlxo49W4gpsp+0foQaJ+OUjGKs9wN0VhUGGPOXisx9TG+uaPhc40TsOub1wh1+5CQc; tfstk=gga-uF1rOsdR699ywJjcKjTB48fcBi0zayyW-e0nEiwxhW1rxWikR2FLUDaut4MQHJcZNufEdETK6JhQrT359wFQ1YTu-goBJxwpAp1yRKgbIXrhaTkClmwZPDroKYDKJWyOiObGS7Pr84XGINf1Ni-E7eGINpmXlf3KNFJ1r_Nr826DiesGW7yu5cYsV21xlXhid2tWVsnjOf3BPDTWcKMqO2gIFYNXlfGnd3iSAsFj3XgIdJgCMqMqO2MQd2GQRaMvOv8Lq7dk-yS55y4gkbn-CSIwJe1nNdDTNxLBRDh-2hNSHeTQlkMJ0EHOkKM0O5rIDyQDu2P0XJEQh6TIpoGTBf2llU3Qc-UtfSW9zYEbUy3obwdKMlFbezVAtneLh5rZPz6erYrQGyM0P6YKClVZkjzh3UMLckao42J5ejU86yEd4VzgW7NXIAhHVsCvYHoSg-05MImoenExMAf-FH-E0flxIsI9YHoSgjHGwTteYmlN.; isg=BAkJy27khPw5Tnh84JuC9T9QGDNjVv2INGQhX6t_hPAv8igE8qekWfdqMFbEkJXA', 1, null, 'unknown', null, '2025-12-19 15:38:51', '2025-12-19 15:38:51');
INSERT INTO file_link_monitor_v2.pan_cookies (id, pan_type, cookie, is_active, last_check_time, check_status, check_error, created_at, updated_at) VALUES (3, 'xunlei', '[
  {
    "domain": ".xunlei.com",
    "expirationDate": 1766750204,
    "hostOnly": false,
    "httpOnly": false,
    "name": "deviceid",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "wdi10.d765a49124d0b4c8d593d73daa738f51134146e64398f5f02515b17ad857699e"
  },
  {
    "domain": ".xunlei.com",
    "expirationDate": 1766750204,
    "hostOnly": false,
    "httpOnly": false,
    "name": "xl_fp_rt",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "1766145394275"
  },
  {
    "domain": ".xunlei.com",
    "expirationDate": 1766647009,
    "hostOnly": false,
    "httpOnly": false,
    "name": "XLA_CI",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "b20bf9f4dbf52a5dafb99e2fd380d96c"
  },
  {
    "domain": ".xunlei.com",
    "hostOnly": false,
    "httpOnly": false,
    "name": "sessionid",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": true,
    "storeId": "0",
    "value": "cs001.F8CD930AA438D3D35B40710F063614E0"
  },
  {
    "domain": ".xunlei.com",
    "expirationDate": 1769227078,
    "hostOnly": false,
    "httpOnly": false,
    "name": "userid",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "683676213"
  },
  {
    "domain": ".xunlei.com",
    "hostOnly": false,
    "httpOnly": false,
    "name": "usernewno",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": true,
    "storeId": "0",
    "value": "1270048342"
  }
]', 1, null, 'unknown', null, '2025-12-19 22:14:13', '2025-12-25 11:58:51');
